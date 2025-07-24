# Configuration Template for Exotel Voice Streaming WebSocket Server
# Copy this file to config.py and modify as needed

# Server Configuration
SERVER_HOST = "0.0.0.0"  # Listen on all interfaces
SERVER_PORT = 5000       # Default port

# Logging Configuration
LOG_LEVEL = "INFO"       # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True       # Save logs to files
LOG_DIRECTORY = "logs"   # Directory for log files

# Audio Configuration
ENABLE_ECHO = True       # Echo back audio in bidirectional mode
AUDIO_FORMAT = "LINEAR16"
SAMPLE_RATE = 8000
CHANNELS = 1

# Optional: Google Speech-to-Text Configuration
# Only needed for unidirectional streaming with transcription
GOOGLE_CREDENTIALS_PATH = None  # Path to service account JSON file
LANGUAGE_CODE = "en-US"         # Speech recognition language

# Optional: Advanced Features
ENABLE_METRICS = True           # Audio quality monitoring
METRICS_INTERVAL = 10          # Log metrics every N seconds
MAX_CONNECTIONS = 100          # Maximum concurrent connections

# ngrok Configuration (for development)
# Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTH_TOKEN = "YOUR_NGROK_TOKEN_HERE"

# Security (for production)
REQUIRE_AUTH = False           # Enable authentication
API_KEY = None                # API key for authentication

# Example usage:
# 1. Copy this file: cp config.example.py config.py
# 2. Edit config.py with your settings
# 3. Import in your server: from config import * 