FROM python:3.11-slim

WORKDIR /app

# Copy requirements from exotel directory
COPY exotel/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the bridge runs on
EXPOSE 10002

# Run the bridge using gunicorn for production reliability
# We use the gevent worker class to support WebSockets via flask-sock
CMD ["gunicorn", "--bind", "0.0.0.0:10002", "--worker-class", "gevent", "--workers", "1", "--timeout", "0", "exotel.bridge:app"]
