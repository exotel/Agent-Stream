#!/bin/bash
#
# Deploy Exotel-ElevenLabs Bridge to a GCP Compute Engine VM
# with ngrok tunnel for a stable custom domain.
#
# Usage:
#   export ELEVENLABS_AGENT_ID="agent_..."
#   export NGROK_AUTHTOKEN="2..."
#   export NGROK_DOMAIN="sultrily-unreckoned-roselia.ngrok-free.dev"
#   # Optional:
#   export ELEVENLABS_API_KEY="..."
#   export ELEVENLABS_REGION="default"       # default|us|eu|india
#   export BG_SOUND_FILE="exotel/assets/office-ambience-loud.wav"
#   export BG_SOUND_VOLUME="0.5"
#   ./deploy_gcp_vm.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VM_NAME="${VM_NAME:-exotel-bridge-vm}"
GCP_ZONE="${GCP_ZONE:-asia-south1-b}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-small}"
ELEVENLABS_REGION="${ELEVENLABS_REGION:-default}"
BG_SOUND_FILE="${BG_SOUND_FILE:-exotel/assets/office-ambience-loud.wav}"
BG_SOUND_VOLUME="${BG_SOUND_VOLUME:-0.5}"
NGROK_DOMAIN="${NGROK_DOMAIN:-sultrily-unreckoned-roselia.ngrok-free.dev}"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
if [ -z "${ELEVENLABS_AGENT_ID:-}" ]; then
    echo "Error: ELEVENLABS_AGENT_ID is not set."
    echo "  export ELEVENLABS_AGENT_ID=your_agent_id"
    exit 1
fi

if [ -z "${NGROK_AUTHTOKEN:-}" ]; then
    echo "Error: NGROK_AUTHTOKEN is not set."
    echo "  Get it from https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project configured. Run: gcloud config set project [PROJECT_ID]"
    exit 1
fi

echo "=============================================="
echo "  Exotel Bridge -> GCP VM Deployment"
echo "=============================================="
echo "  Project:     $PROJECT_ID"
echo "  VM:          $VM_NAME"
echo "  Zone:        $GCP_ZONE"
echo "  Machine:     $MACHINE_TYPE"
echo "  Agent ID:    $ELEVENLABS_AGENT_ID"
echo "  EL Region:   $ELEVENLABS_REGION"
echo "  ngrok domain: $NGROK_DOMAIN"
echo "  BG Sound:    $BG_SOUND_FILE (vol=$BG_SOUND_VOLUME)"
echo "=============================================="

# ---------------------------------------------------------------------------
# 1. Create the VM (skip if it already exists)
# ---------------------------------------------------------------------------
if gcloud compute instances describe "$VM_NAME" --zone="$GCP_ZONE" &>/dev/null; then
    echo "VM $VM_NAME already exists -- reusing."
else
    echo "Creating VM $VM_NAME ..."
    gcloud compute instances create "$VM_NAME" \
        --zone="$GCP_ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --boot-disk-size=20GB \
        --tags=http-server,https-server \
        --metadata=startup-script='#!/bin/bash
apt-get update -qq'

    echo "Waiting for VM to be ready..."
    sleep 30
fi

# Allow HTTP/HTTPS if firewall rules don't exist yet
gcloud compute firewall-rules describe allow-http &>/dev/null 2>&1 || \
    gcloud compute firewall-rules create allow-http \
        --allow tcp:80,tcp:443,tcp:10002 \
        --target-tags=http-server 2>/dev/null || true

# ---------------------------------------------------------------------------
# 2. Copy project files to the VM
# ---------------------------------------------------------------------------
echo "Uploading project files..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create a tar of the project excluding unnecessary files
TMPTAR=$(mktemp /tmp/exotel-bridge-XXXXXX.tar.gz)
tar -czf "$TMPTAR" \
    -C "$SCRIPT_DIR" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='exotel/logs' \
    --exclude='*.pyc' \
    --exclude='node_modules' \
    .

gcloud compute scp "$TMPTAR" "$VM_NAME:~/bridge.tar.gz" --zone="$GCP_ZONE" --tunnel-through-iap
rm -f "$TMPTAR"

# ---------------------------------------------------------------------------
# 3. SSH in and set everything up
# ---------------------------------------------------------------------------
echo "Setting up the VM..."

gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="$(cat <<'REMOTE_SETUP'
set -euo pipefail

echo ">>> Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv curl

echo ">>> Installing ngrok..."
if ! command -v ngrok &>/dev/null; then
    curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
        | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
        | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt-get update -qq
    sudo apt-get install -y -qq ngrok
fi

echo ">>> Extracting project files..."
sudo mkdir -p /opt/exotel-bridge
sudo tar -xzf ~/bridge.tar.gz -C /opt/exotel-bridge
sudo chown -R root:root /opt/exotel-bridge
rm -f ~/bridge.tar.gz

echo ">>> Setting up Python venv & deps..."
sudo python3 -m venv /opt/exotel-bridge/venv
sudo /opt/exotel-bridge/venv/bin/pip install --quiet -r /opt/exotel-bridge/exotel/requirements.txt

echo ">>> Base setup complete."
REMOTE_SETUP
)"

# Now configure ngrok auth token and create systemd services (needs env vars)
echo "Configuring ngrok and systemd services..."

gcloud compute ssh "$VM_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="
set -euo pipefail

# Configure ngrok
sudo ngrok config add-authtoken '$NGROK_AUTHTOKEN'

# ---- systemd: exotel-bridge ----
sudo tee /etc/systemd/system/exotel-bridge.service >/dev/null <<EOF
[Unit]
Description=Exotel-ElevenLabs Bridge
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/exotel-bridge
Environment=ELEVENLABS_AGENT_ID=$ELEVENLABS_AGENT_ID
Environment=ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-}
Environment=ELEVENLABS_REGION=$ELEVENLABS_REGION
Environment=BG_SOUND_FILE=$BG_SOUND_FILE
Environment=BG_SOUND_VOLUME=$BG_SOUND_VOLUME
ExecStart=/opt/exotel-bridge/venv/bin/gunicorn \
    --bind 0.0.0.0:10002 \
    --worker-class gevent \
    --workers 1 \
    --timeout 0 \
    exotel.bridge:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# ---- systemd: ngrok-tunnel ----
sudo tee /etc/systemd/system/ngrok-tunnel.service >/dev/null <<EOF
[Unit]
Description=ngrok tunnel for Exotel Bridge
After=network.target exotel-bridge.service

[Service]
Type=simple
ExecStart=/usr/local/bin/ngrok http 10002 --domain $NGROK_DOMAIN --log=stdout
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable exotel-bridge ngrok-tunnel
sudo systemctl restart exotel-bridge
sleep 3
sudo systemctl restart ngrok-tunnel

echo '>>> Services started. Checking status...'
sudo systemctl status exotel-bridge --no-pager -l || true
echo '---'
sudo systemctl status ngrok-tunnel --no-pager -l || true
"

echo ""
echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo "  VM:          $VM_NAME ($GCP_ZONE)"
echo "  ngrok URL:   https://$NGROK_DOMAIN"
echo "  WebSocket:   wss://$NGROK_DOMAIN/v1/convai/conversation/exotel"
echo "  Health:      https://$NGROK_DOMAIN/health"
echo "  BG Control:  POST https://$NGROK_DOMAIN/bg-sound"
echo ""
echo "  SSH into VM: gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --tunnel-through-iap"
echo "  View logs:   gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --tunnel-through-iap --command='sudo journalctl -u exotel-bridge -f'"
echo "  View ngrok:  gcloud compute ssh $VM_NAME --zone=$GCP_ZONE --tunnel-through-iap --command='sudo journalctl -u ngrok-tunnel -f'"
echo "=============================================="
