#!/bin/bash

# AWS Deployment Script for Exotel-ElevenLabs Bridge
# Uses ECS Fargate + ALB (Application Load Balancer) for WebSocket support.
# App Runner does not reliably support WebSocket upgrades.

set -e

# Configuration
SERVICE_NAME="exotel-bridge"
AWS_REGION="${AWS_REGION:-ap-south-1}"
ECR_REPO_NAME="exotel-bridge-repo"
CLUSTER_NAME="exotel-bridge-cluster"
CONTAINER_PORT=10002

ELEVENLABS_REGION="${ELEVENLABS_REGION:-india}"

# Check for required environment variables
if [ -z "$ELEVENLABS_AGENT_ID" ]; then
    echo "Error: ELEVENLABS_AGENT_ID is not set."
    echo "Please set it: export ELEVENLABS_AGENT_ID=your_agent_id"
    exit 1
fi

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "Warning: ELEVENLABS_API_KEY is not set."
fi

echo "=============================================="
echo "ElevenLabs Configuration:"
echo "  Agent ID: $ELEVENLABS_AGENT_ID"
echo "  Region:   $ELEVENLABS_REGION"
case "$ELEVENLABS_REGION" in
    "india")  echo "  API URL:  wss://api.in.residency.elevenlabs.io" ;;
    "eu")     echo "  API URL:  wss://api.eu.residency.elevenlabs.io" ;;
    "us")     echo "  API URL:  wss://api.us.elevenlabs.io" ;;
    *)        echo "  API URL:  wss://api.elevenlabs.io" ;;
esac
echo "=============================================="

if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    echo "Error: Could not retrieve AWS Account ID. Run 'aws configure' first."
    exit 1
fi

echo "Deploying to AWS account $ACCOUNT_ID in $AWS_REGION..."

# ---------- 1. ECR: Create repo, build & push image ----------

echo "Checking ECR repository: $ECR_REPO_NAME..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPO_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo "Creating ECR repository..."
    aws ecr create-repository --repository-name "$ECR_REPO_NAME" --region "$AWS_REGION" --no-cli-pager
fi

echo "Logging into ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

IMAGE_URL="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:latest"
echo "Building container image..."
docker build -t "$ECR_REPO_NAME" .
docker tag "$ECR_REPO_NAME:latest" "$IMAGE_URL"

echo "Pushing image to ECR..."
docker push "$IMAGE_URL"

# ---------- 2. IAM: ECS task execution role ----------

TASK_EXEC_ROLE="ecsTaskExecutionRole"
echo "Checking IAM role: $TASK_EXEC_ROLE..."
if ! aws iam get-role --role-name "$TASK_EXEC_ROLE" > /dev/null 2>&1; then
    echo "Creating ECS task execution role..."
    aws iam create-role \
        --role-name "$TASK_EXEC_ROLE" \
        --assume-role-policy-document '{
          "Version": "2012-10-17",
          "Statement": [{
            "Effect": "Allow",
            "Principal": { "Service": "ecs-tasks.amazonaws.com" },
            "Action": "sts:AssumeRole"
          }]
        }' --no-cli-pager

    aws iam attach-role-policy \
        --role-name "$TASK_EXEC_ROLE" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

    echo "Waiting for IAM propagation..."
    sleep 10
fi

TASK_EXEC_ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$TASK_EXEC_ROLE"

# ---------- 3. Networking: Default VPC, subnets, security groups ----------

echo "Looking up default VPC..."
VPC_ID=$(aws ec2 describe-vpcs --region "$AWS_REGION" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text)
if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
    echo "Error: No default VPC found in $AWS_REGION. Create one with: aws ec2 create-default-vpc --region $AWS_REGION"
    exit 1
fi
echo "  VPC: $VPC_ID"

SUBNET_IDS=$(aws ec2 describe-subnets --region "$AWS_REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=default-for-az,Values=true" \
    --query "Subnets[].SubnetId" --output text)
SUBNET_CSV=$(echo "$SUBNET_IDS" | tr '\t' ',')
echo "  Subnets: $SUBNET_CSV"

# Security group for ALB (allow inbound 80/443)
ALB_SG_NAME="${SERVICE_NAME}-alb-sg"
ALB_SG_ID=$(aws ec2 describe-security-groups --region "$AWS_REGION" \
    --filters "Name=group-name,Values=$ALB_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)

if [ -z "$ALB_SG_ID" ] || [ "$ALB_SG_ID" == "None" ]; then
    echo "Creating ALB security group..."
    ALB_SG_ID=$(aws ec2 create-security-group --region "$AWS_REGION" \
        --group-name "$ALB_SG_NAME" --description "ALB for $SERVICE_NAME" \
        --vpc-id "$VPC_ID" --query "GroupId" --output text)
    aws ec2 authorize-security-group-ingress --region "$AWS_REGION" \
        --group-id "$ALB_SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 --no-cli-pager
    aws ec2 authorize-security-group-ingress --region "$AWS_REGION" \
        --group-id "$ALB_SG_ID" --protocol tcp --port 443 --cidr 0.0.0.0/0 --no-cli-pager
fi
echo "  ALB SG: $ALB_SG_ID"

# Security group for ECS tasks (allow traffic from ALB only)
TASK_SG_NAME="${SERVICE_NAME}-task-sg"
TASK_SG_ID=$(aws ec2 describe-security-groups --region "$AWS_REGION" \
    --filters "Name=group-name,Values=$TASK_SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[0].GroupId" --output text 2>/dev/null)

if [ -z "$TASK_SG_ID" ] || [ "$TASK_SG_ID" == "None" ]; then
    echo "Creating task security group..."
    TASK_SG_ID=$(aws ec2 create-security-group --region "$AWS_REGION" \
        --group-name "$TASK_SG_NAME" --description "ECS tasks for $SERVICE_NAME" \
        --vpc-id "$VPC_ID" --query "GroupId" --output text)
    aws ec2 authorize-security-group-ingress --region "$AWS_REGION" \
        --group-id "$TASK_SG_ID" --protocol tcp --port "$CONTAINER_PORT" \
        --source-group "$ALB_SG_ID" --no-cli-pager
fi
echo "  Task SG: $TASK_SG_ID"

# ---------- 4. ALB + Target Group ----------

ALB_NAME="${SERVICE_NAME}-alb"
TG_NAME="${SERVICE_NAME}-tg"

ALB_ARN=$(aws elbv2 describe-load-balancers --region "$AWS_REGION" \
    --names "$ALB_NAME" --query "LoadBalancers[0].LoadBalancerArn" --output text 2>/dev/null || echo "None")

if [ "$ALB_ARN" == "None" ] || [ -z "$ALB_ARN" ]; then
    echo "Creating Application Load Balancer..."
    ALB_ARN=$(aws elbv2 create-load-balancer --region "$AWS_REGION" \
        --name "$ALB_NAME" --subnets $SUBNET_IDS \
        --security-groups "$ALB_SG_ID" --scheme internet-facing \
        --type application --query "LoadBalancers[0].LoadBalancerArn" --output text)
    echo "  Waiting for ALB to become active..."
    aws elbv2 wait load-balancer-available --region "$AWS_REGION" --load-balancer-arns "$ALB_ARN"
fi
echo "  ALB: $ALB_ARN"

TG_ARN=$(aws elbv2 describe-target-groups --region "$AWS_REGION" \
    --names "$TG_NAME" --query "TargetGroups[0].TargetGroupArn" --output text 2>/dev/null || echo "None")

if [ "$TG_ARN" == "None" ] || [ -z "$TG_ARN" ]; then
    echo "Creating target group..."
    TG_ARN=$(aws elbv2 create-target-group --region "$AWS_REGION" \
        --name "$TG_NAME" --protocol HTTP --port "$CONTAINER_PORT" \
        --vpc-id "$VPC_ID" --target-type ip \
        --health-check-path "/health" --health-check-interval-seconds 30 \
        --healthy-threshold-count 2 --unhealthy-threshold-count 3 \
        --query "TargetGroups[0].TargetGroupArn" --output text)

    # Enable stickiness for WebSocket connections
    aws elbv2 modify-target-group-attributes --region "$AWS_REGION" \
        --target-group-arn "$TG_ARN" \
        --attributes Key=stickiness.enabled,Value=true Key=stickiness.type,Value=lb_cookie Key=stickiness.lb_cookie.duration_seconds,Value=3600 \
        --no-cli-pager
fi
echo "  Target Group: $TG_ARN"

# Create HTTP listener if it doesn't exist
LISTENER_ARN=$(aws elbv2 describe-listeners --region "$AWS_REGION" \
    --load-balancer-arn "$ALB_ARN" --query "Listeners[?Port==\`80\`].ListenerArn" --output text 2>/dev/null)

if [ -z "$LISTENER_ARN" ] || [ "$LISTENER_ARN" == "None" ]; then
    echo "Creating HTTP listener..."
    LISTENER_ARN=$(aws elbv2 create-listener --region "$AWS_REGION" \
        --load-balancer-arn "$ALB_ARN" --protocol HTTP --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
        --query "Listeners[0].ListenerArn" --output text)
fi

# ---------- 5. ECS: Cluster + Task Definition + Service ----------

echo "Checking ECS cluster..."
CLUSTER_STATUS=$(aws ecs describe-clusters --region "$AWS_REGION" \
    --clusters "$CLUSTER_NAME" --query "clusters[0].status" --output text 2>/dev/null || echo "MISSING")

if [ "$CLUSTER_STATUS" != "ACTIVE" ]; then
    echo "Creating ECS cluster..."
    aws ecs create-cluster --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME" --no-cli-pager
fi

echo "Registering task definition..."
TASK_DEF_JSON=$(cat <<TASKEOF
{
  "family": "$SERVICE_NAME",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$TASK_EXEC_ROLE_ARN",
  "containerDefinitions": [{
    "name": "$SERVICE_NAME",
    "image": "$IMAGE_URL",
    "portMappings": [{
      "containerPort": $CONTAINER_PORT,
      "protocol": "tcp"
    }],
    "environment": [
      { "name": "ELEVENLABS_AGENT_ID", "value": "$ELEVENLABS_AGENT_ID" },
      { "name": "ELEVENLABS_API_KEY",  "value": "${ELEVENLABS_API_KEY:-}" },
      { "name": "ELEVENLABS_REGION",   "value": "$ELEVENLABS_REGION" }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/$SERVICE_NAME",
        "awslogs-region": "$AWS_REGION",
        "awslogs-stream-prefix": "ecs",
        "awslogs-create-group": "true"
      }
    }
  }]
}
TASKEOF
)

TASK_DEF_ARN=$(aws ecs register-task-definition --region "$AWS_REGION" \
    --cli-input-json "$TASK_DEF_JSON" \
    --query "taskDefinition.taskDefinitionArn" --output text)
echo "  Task definition: $TASK_DEF_ARN"

# Create or update ECS service
ECS_SERVICE_STATUS=$(aws ecs describe-services --region "$AWS_REGION" \
    --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" \
    --query "services[0].status" --output text 2>/dev/null || echo "MISSING")

if [ "$ECS_SERVICE_STATUS" == "ACTIVE" ]; then
    echo "Updating ECS service..."
    aws ecs update-service --region "$AWS_REGION" \
        --cluster "$CLUSTER_NAME" --service "$SERVICE_NAME" \
        --task-definition "$TASK_DEF_ARN" --force-new-deployment \
        --no-cli-pager > /dev/null
else
    echo "Creating ECS service..."
    aws ecs create-service --region "$AWS_REGION" \
        --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" \
        --task-definition "$TASK_DEF_ARN" --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_CSV],securityGroups=[$TASK_SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TG_ARN,containerName=$SERVICE_NAME,containerPort=$CONTAINER_PORT" \
        --no-cli-pager > /dev/null
fi

# ---------- 6. Output ----------

ALB_DNS=$(aws elbv2 describe-load-balancers --region "$AWS_REGION" \
    --load-balancer-arns "$ALB_ARN" --query "LoadBalancers[0].DNSName" --output text)

echo ""
echo "=============================================="
echo "Deployment initiated!"
echo "=============================================="
echo "Service:     $SERVICE_NAME"
echo "AWS Region:  $AWS_REGION"
echo "EL Region:   $ELEVENLABS_REGION"
echo "----------------------------------------------"
echo "WebSocket URL for Exotel applet:"
echo "  ws://$ALB_DNS/v1/convai/conversation/exotel?agent_id=$ELEVENLABS_AGENT_ID"
echo ""
echo "Health Check:"
echo "  http://$ALB_DNS/health"
echo "----------------------------------------------"
echo ""
echo "For wss:// (recommended), add an ACM certificate"
echo "and HTTPS listener on port 443 to the ALB."
echo ""
echo "Monitor:"
echo "  aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'"
echo ""
echo "Logs:"
echo "  aws logs tail /ecs/$SERVICE_NAME --region $AWS_REGION --follow"
echo "=============================================="
