# Production Dockerfile for Voice AI Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 voiceai && \
    mkdir -p /app/logs && \
    chown -R voiceai:voiceai /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements-production.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-production.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs engines static templates && \
    chown -R voiceai:voiceai /app

# Switch to non-root user
USER voiceai

# Expose ports
EXPOSE 5000 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

# Default command
CMD ["python", "production_launcher.py"] 