#!/usr/bin/env python3
"""
Setup script for Exotel Voice Streaming Server
This script helps configure the server with the correct IP address and provides setup instructions.
"""

import requests
import socket
import subprocess
import sys
import os
from datetime import datetime

def get_public_ip():
    """Get the public IP address of the machine."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except Exception as e:
        print(f"Could not get public IP: {e}")
        return None

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Could not get local IP: {e}")
        return None

def check_port_availability(port):
    """Check if a port is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0  # Port is available if result != 0
    except:
        return False

def create_nginx_config(public_ip, port):
    """Create nginx configuration for reverse proxy."""
    config = f"""
# Nginx configuration for Exotel Voice Streaming
# Save this as /etc/nginx/sites-available/exotel-streaming

server {{
    listen 80;
    server_name {public_ip};

    location / {{
        proxy_pass http://localhost:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }}
}}
"""
    return config

def main():
    print("🚀 Exotel Voice Streaming Server Setup")
    print("=" * 50)
    
    # Get IP addresses
    public_ip = get_public_ip()
    local_ip = get_local_ip()
    
    print(f"📍 Public IP: {public_ip}")
    print(f"🏠 Local IP: {local_ip}")
    print()
    
    # Check port availability
    port = 5000
    if not check_port_availability(port):
        print(f"⚠️  Port {port} is already in use!")
        print("   Please stop any existing services on this port or use a different port.")
        return
    
    print(f"✅ Port {port} is available")
    print()
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    print("📁 Created logs directory")
    
    # Generate configuration
    print("\n🔧 Configuration:")
    print(f"   WebSocket URL: ws://{public_ip}:{port}/media")
    print(f"   HTTP URL: http://{public_ip}:{port}")
    print()
    
    # Instructions for Exotel
    print("📋 Exotel Configuration:")
    print("   In your Exotel flow, use the following URL:")
    print(f"   ws://{public_ip}:{port}/media")
    print()
    
    # Firewall instructions
    print("🔥 Firewall Setup:")
    print("   Make sure port 5000 is open in your firewall:")
    print("   - AWS: Add to Security Group")
    print("   - GCP: Add to Firewall Rules")
    print("   - Azure: Add to Network Security Group")
    print("   - Local: Configure your router/firewall")
    print()
    
    # Nginx setup (optional)
    if public_ip:
        print("🌐 Optional: Nginx Reverse Proxy Setup")
        print("   If you want to use nginx as a reverse proxy:")
        nginx_config = create_nginx_config(public_ip, port)
        with open('nginx_exotel_config.conf', 'w') as f:
            f.write(nginx_config)
        print("   ✅ Created nginx_exotel_config.conf")
        print("   Copy this file to /etc/nginx/sites-available/")
        print("   Then enable it with: sudo ln -s /etc/nginx/sites-available/exotel-streaming /etc/nginx/sites-enabled/")
        print()
    
    # Start server command
    print("🚀 To start the server:")
    print("   # For bidirectional streaming (echo):")
    print(f"   python app.py --stream_type bidirectional --port {port} --host 0.0.0.0")
    print()
    print("   # For unidirectional streaming (transcription):")
    print(f"   python app.py --stream_type unidirectional --port {port} --host 0.0.0.0")
    print()
    
    # Logging information
    print("📊 Logging:")
    print("   - Console logs: Real-time output")
    print("   - File logs: logs/voice_streaming.log")
    print("   - Event logs: logs/events.log")
    print()
    
    # Test connection
    print("🧪 Testing:")
    print("   Run this to test the connection:")
    print("   python test_server.py")
    print()
    
    # Save configuration
    config_data = {
        'timestamp': datetime.now().isoformat(),
        'public_ip': public_ip,
        'local_ip': local_ip,
        'port': port,
        'websocket_url': f"ws://{public_ip}:{port}/media" if public_ip else None,
        'http_url': f"http://{public_ip}:{port}" if public_ip else None
    }
    
    import json
    with open('server_config.json', 'w') as f:
        json.dump(config_data, f, indent=2)
    
    print("💾 Configuration saved to server_config.json")
    print()
    
    print("✅ Setup complete! Your server is ready for Exotel integration.")
    print()
    print("📞 Next steps:")
    print("   1. Start the server using one of the commands above")
    print("   2. Configure your Exotel flow with the WebSocket URL")
    print("   3. Test with a real call")
    print("   4. Monitor logs for debugging")

if __name__ == "__main__":
    main() 