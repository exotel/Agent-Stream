#!/bin/bash

# GCP Deployment Script for Exotel-ElevenLabs Bridge
# This script builds a container and deploys it to Google Cloud Run

# Exit on error
set -e

# Configuration
SERVICE_NAME="exotel-bridge"
GCP_REGION="${GCP_REGION:-asia-south1}"  # Default to Mumbai for lower latency to India

# ElevenLabs region configuration
# Options: default, us, eu, india
# For India residency, use "india" which connects to api.in.residency.elevenlabs.io
ELEVENLABS_REGION="${ELEVENLABS_REGION:-india}"

# Check for required environment variables
if [ -z "$ELEVENLABS_AGENT_ID" ]; then
    echo "Error: ELEVENLABS_AGENT_ID is not set."
    echo "Please set it: export ELEVENLABS_AGENT_ID=your_agent_id"
    exit 1
fi

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "Warning: ELEVENLABS_API_KEY is not set. Some features may not work."
fi

echo "=============================================="
echo "ElevenLabs Configuration:"
echo "  Agent ID: $ELEVENLABS_AGENT_ID"
echo "  Region:   $ELEVENLABS_REGION"
case "$ELEVENLABS_REGION" in
    "india")
        echo "  API URL:  wss://api.in.residency.elevenlabs.io"
        ;;
    "eu")
        echo "  API URL:  wss://api.eu.residency.elevenlabs.io"
        ;;
    "us")
        echo "  API URL:  wss://api.us.elevenlabs.io"
        ;;
    *)
        echo "  API URL:  wss://api.elevenlabs.io"
        ;;
esac
echo "=============================================="

# Get GCP Project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP project configured. Run 'gcloud config set project [PROJECT_ID]'"
    exit 1
fi

echo "Deploying $SERVICE_NAME to GCP project $PROJECT_ID in $GCP_REGION..."

# Enable necessary services
echo "Enabling GCP services..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# Build and Push using Cloud Build
echo "Building container image..."
IMAGE_URL="gcr.io/$PROJECT_ID/$SERVICE_NAME"
gcloud builds submit --tag "$IMAGE_URL" .

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URL" \
    --platform managed \
    --region "$GCP_REGION" \
    --allow-unauthenticated \
    --port 10002 \
    --set-env-vars "ELEVENLABS_AGENT_ID=$ELEVENLABS_AGENT_ID,ELEVENLABS_API_KEY=$ELEVENLABS_API_KEY,ELEVENLABS_REGION=$ELEVENLABS_REGION"

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform managed --region "$GCP_REGION" --format 'value(status.url)')

# Convert to WebSocket URL
WS_URL=$(echo "$SERVICE_URL" | sed 's/https:\/\//wss:\/\//')
WS_ENDPOINT="$WS_URL/media"

echo -e "\n=============================================="
echo "Deployment Successful!"
echo "=============================================="
echo "Service:        $SERVICE_NAME"
echo "GCP Region:     $GCP_REGION"
echo "EL Region:      $ELEVENLABS_REGION"
echo "----------------------------------------------"
echo "WebSocket URL for Exotel:"
echo "  $WS_ENDPOINT"
echo ""
echo "Health Check:"
echo "  $SERVICE_URL/health"
echo "=============================================="
