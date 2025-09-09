# OpenAI Realtime Bot - Production Dockerfile
# ==========================================
#
# Multi-stage build for production deployment
# Optimized for size, security, and performance
#
# Author: Agent Stream Team
# Version: 2.0.0

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=2.0.0
ARG VCS_REF

# Add metadata
LABEL maintainer="Agent Stream Team" \
      version="${VERSION}" \
      description="OpenAI Realtime Bot Framework" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libasound2 \
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY logs/ ./logs/
COPY .env.production ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "src/core/realtime_bot.py"] 