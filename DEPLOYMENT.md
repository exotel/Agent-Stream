# Deployment Guide

This guide covers deploying the OpenAI Realtime Bot Framework in various environments.

## Prerequisites

- Python 3.8+
- Docker (for containerized deployment)
- Kubernetes cluster (for K8s deployment)
- Valid OpenAI API key with Realtime API access

## Environment Setup

### 1. Local Development

```bash
# Clone and setup
git clone https://github.com/your-username/openai-realtime-bot.git
cd openai-realtime-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your configuration
```

### 2. Docker Deployment

```bash
# Build image
docker build -t openai-realtime-bot .

# Run with environment file
docker run --env-file .env -p 5000:5000 openai-realtime-bot

# Or use docker-compose
docker-compose up -d
```

### 3. Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace realtime-bot

# Create secret for API keys
kubectl create secret generic bot-secrets \
  --from-literal=openai-api-key=your_api_key_here \
  -n realtime-bot

# Deploy application
kubectl apply -f k8s/ -n realtime-bot

# Check deployment
kubectl get pods -n realtime-bot
```

## Production Considerations

### Scaling

- **Horizontal Scaling**: Deploy multiple bot instances behind a load balancer
- **Vertical Scaling**: Increase CPU/memory for higher concurrent connections
- **Database**: Use external database for session storage in multi-instance setup

### Monitoring

- **Health Checks**: Implement `/health` endpoint monitoring
- **Metrics**: Use Prometheus/Grafana for performance monitoring  
- **Logging**: Centralized logging with ELK stack or similar
- **Alerting**: Set up alerts for high error rates or downtime

### Security

- **TLS/SSL**: Always use HTTPS/WSS in production
- **Firewall**: Restrict access to necessary ports only
- **API Keys**: Use secure key management (AWS Secrets Manager, etc.)
- **Network**: Deploy in private subnets with proper security groups

## Cloud Provider Specific

### AWS Deployment

```bash
# Using ECS
aws ecs create-cluster --cluster-name realtime-bot-cluster

# Using EKS
eksctl create cluster --name realtime-bot --region us-west-2
```

### Google Cloud Deployment

```bash
# Using Cloud Run
gcloud run deploy realtime-bot --image gcr.io/project/realtime-bot

# Using GKE
gcloud container clusters create realtime-bot-cluster
```

### Azure Deployment

```bash
# Using Container Instances
az container create --resource-group myResourceGroup \
  --name realtime-bot --image myregistry.azurecr.io/realtime-bot

# Using AKS
az aks create --resource-group myResourceGroup --name realtime-bot-cluster
```

## Performance Tuning

### Audio Processing
- Adjust `MAX_CHUNK_SIZE_MS` based on latency requirements
- Enable `DYNAMIC_CHUNK_SIZING` for adaptive performance
- Monitor CPU usage during peak loads

### Connection Management
- Set appropriate connection timeouts
- Implement connection pooling for database access
- Use Redis for session caching in multi-instance deployments

### Resource Allocation
- **CPU**: 1-2 cores per 50 concurrent connections
- **Memory**: 512MB-1GB per instance
- **Network**: Ensure sufficient bandwidth for audio streaming

## Troubleshooting

### Common Issues

1. **High Latency**: Check network connectivity to OpenAI API
2. **Connection Drops**: Verify WebSocket timeout settings
3. **Audio Quality**: Ensure proper sample rate configuration
4. **Memory Leaks**: Monitor for unclosed connections

### Debugging

```bash
# Check logs
kubectl logs -f deployment/realtime-bot -n realtime-bot

# Debug networking
kubectl exec -it pod/realtime-bot-xxx -- netstat -an

# Performance monitoring
kubectl top pods -n realtime-bot
```

## Rollback Procedures

### Docker
```bash
# Rollback to previous version
docker-compose down
docker-compose up -d --scale bot=0
docker-compose up -d
```

### Kubernetes
```bash
# Rollback deployment
kubectl rollout undo deployment/realtime-bot -n realtime-bot

# Check rollout status
kubectl rollout status deployment/realtime-bot -n realtime-bot
```

## Maintenance

### Regular Tasks
- Update dependencies monthly
- Rotate API keys quarterly
- Review and update security configurations
- Monitor and optimize performance metrics
- Backup configuration and deployment scripts

### Updates
- Test updates in staging environment first
- Use blue-green deployment for zero-downtime updates
- Monitor error rates after deployments
- Have rollback plan ready

