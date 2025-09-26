# Docker Hub Deployment Guide

This guide covers deploying FundLink to production using Docker Hub and container orchestration platforms.

## Overview

We'll push multi-stage Docker images to Docker Hub and deploy them to your chosen platform (Railway, Render, DigitalOcean, AWS, etc.).

## Prerequisites

- Docker Hub account
- Docker installed locally
- Your FundLink repository

## Step 1: Prepare Production Dockerfiles

### 1.1 Update Dockerfile for Production

The current Dockerfile uses development servers. Let's create production-ready commands:

```dockerfile
# Update the web service CMD for production
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "fundlink_backend.wsgi:application"]
```

### 1.2 Create .dockerignore

Create `.dockerignore` to optimize build:
```
.git
.gitignore
README.md
Dockerfile
.dockerignore
.env*
.venv
**/__pycache__
**/*.pyc
node_modules
.pytest_cache
db.sqlite3
```

## Step 2: Build and Push to Docker Hub

### 2.1 Login to Docker Hub

```bash
docker login
```

### 2.2 Build Multi-Stage Images

```bash
# Replace 'yourusername' with your Docker Hub username
DOCKER_USERNAME="yourusername"

# Build web service
docker build --target web -t $DOCKER_USERNAME/fundlink-web:latest .

# Build bot service  
docker build --target bot -t $DOCKER_USERNAME/fundlink-bot:latest .

# Build verifier service
docker build --target verifier -t $DOCKER_USERNAME/fundlink-verifier:latest .
```

### 2.3 Push to Docker Hub

```bash
# Push all images
docker push $DOCKER_USERNAME/fundlink-web:latest
docker push $DOCKER_USERNAME/fundlink-bot:latest  
docker push $DOCKER_USERNAME/fundlink-verifier:latest
```

### 2.4 Tag Specific Versions (Optional)

```bash
# Tag with version number
docker tag $DOCKER_USERNAME/fundlink-web:latest $DOCKER_USERNAME/fundlink-web:v1.0.0
docker push $DOCKER_USERNAME/fundlink-web:v1.0.0
```

## Step 3: Production Docker Compose

Create `docker-compose.hub.yml` for production deployment:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-fundlink}
      POSTGRES_USER: ${POSTGRES_USER:-fundlink}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - fundlink-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-fundlink}"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - fundlink-network

  web:
    image: yourusername/fundlink-web:latest  # Replace with your username
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-fundlink}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-fundlink}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=false
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
      - AVALANCHE_RPC_URL=${AVALANCHE_RPC_URL:-https://api.avax-test.network/ext/bc/C/rpc}
      - AVALANCHE_CHAIN_ID=${AVALANCHE_CHAIN_ID:-43113}
      - USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS:-0x5425890298aed601595a70AB815c96711a31Bc65}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - fundlink-network
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             gunicorn --bind 0.0.0.0:8000 --workers 3 fundlink_backend.wsgi:application"

  bot:
    image: yourusername/fundlink-bot:latest  # Replace with your username
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_WEBHOOK_URL=${TELEGRAM_WEBHOOK_URL}
      - PUBLIC_WEBHOOK_BASE=${PUBLIC_WEBHOOK_BASE}
      - TELEGRAM_WEBHOOK_SECRET=${TELEGRAM_WEBHOOK_SECRET}
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
      - TOGETHER_API_KEY=${TOGETHER_API_KEY}
      - TOGETHER_MODEL=${TOGETHER_MODEL:-meta-llama/Llama-3.1-8B-Instruct}
      - TOGETHER_MODEL_FALLBACK=${TOGETHER_MODEL_FALLBACK:-meta-llama/Llama-3.1-8B-Instruct}
      - LLM_TEMPERATURE=${LLM_TEMPERATURE:-0.2}
      - HTTP_TIMEOUT=${HTTP_TIMEOUT:-20}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - web
    networks:
      - fundlink-network
    restart: unless-stopped

  verifier:
    image: yourusername/fundlink-verifier:latest  # Replace with your username
    environment:
      - AVALANCHE_RPC_URL=${AVALANCHE_RPC_URL:-https://api.avax-test.network/ext/bc/C/rpc}
      - AVALANCHE_CHAIN_ID=${AVALANCHE_CHAIN_ID:-43113}
      - USDT_CONTRACT_ADDRESS=${USDT_CONTRACT_ADDRESS:-0x5425890298aed601595a70AB815c96711a31Bc65}
      - INTERNAL_API_KEY=${INTERNAL_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    depends_on:
      - web
    networks:
      - fundlink-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  fundlink-network:
    driver: bridge
```

## Step 4: Deployment Options

### Option A: VPS/Cloud Server

1. **Set up your server** (Ubuntu/Debian recommended)
2. **Install Docker and Docker Compose**
3. **Create production environment file**:

```bash
# Create .env.production
cat > .env.production << EOF
# Database
POSTGRES_DB=fundlink_prod
POSTGRES_USER=fundlink_prod
POSTGRES_PASSWORD=your-secure-password

# Django
SECRET_KEY=your-super-secret-key-generate-new-one
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
INTERNAL_API_KEY=your-secure-internal-api-key

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/bot/api/webhook/telegram/
PUBLIC_WEBHOOK_BASE=https://yourdomain.com
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret

# LLM
TOGETHER_API_KEY=your-together-api-key

# Blockchain
AVALANCHE_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
AVALANCHE_CHAIN_ID=43113
USDT_CONTRACT_ADDRESS=0x5425890298aed601595a70AB815c96711a31Bc65
EOF
```

4. **Deploy**:
```bash
# Deploy with production environment
docker-compose -f docker-compose.hub.yml --env-file .env.production up -d
```

### Option B: Railway with Docker Hub

1. **Create `railway.toml`**:
```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 300
restartPolicyType = "on-failure"
```

2. **Deploy each service separately**:
```bash
# Deploy web service
railway up --service web

# Deploy bot service  
railway up --service bot

# Deploy verifier service
railway up --service verifier
```

### Option C: DigitalOcean App Platform

Create `app.yaml`:
```yaml
name: fundlink
services:
- name: web
  image:
    registry_type: DOCKER_HUB
    registry: yourusername
    repository: fundlink-web
    tag: latest
  http_port: 8000
  instance_count: 1
  instance_size_slug: basic-xxs
  routes:
  - path: /
  envs:
  - key: SECRET_KEY
    value: your-secret-key
  - key: INTERNAL_API_KEY  
    value: your-api-key

- name: bot
  image:
    registry_type: DOCKER_HUB
    registry: yourusername  
    repository: fundlink-bot
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: TELEGRAM_BOT_TOKEN
    value: your-bot-token

- name: verifier
  image:
    registry_type: DOCKER_HUB
    registry: yourusername
    repository: fundlink-verifier  
    tag: latest
  instance_count: 1
  instance_size_slug: basic-xxs

databases:
- engine: PG
  name: fundlink-db
  num_nodes: 1
  size: basic-xs
  version: "15"
```

## Step 5: Webhook Configuration

After deployment, update your webhook URL:

### Automatic Method (Recommended)
The bot will automatically set the webhook when it starts if `TELEGRAM_WEBHOOK_URL` is configured.

### Manual Method
```bash
# Get your deployment URL and set webhook manually
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://yourdomain.com/bot/api/webhook/telegram/",
       "secret_token": "'${TELEGRAM_WEBHOOK_SECRET}'"
     }'
```

## Step 6: SSL/HTTPS Setup

### For VPS Deployment:
1. **Install Nginx**:
```bash
sudo apt install nginx certbot python3-certbot-nginx
```

2. **Configure Nginx** (`/etc/nginx/sites-available/fundlink`):
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Get SSL Certificate**:
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Step 7: Monitoring and Maintenance

### Health Checks
```bash
# Check all services
docker-compose -f docker-compose.hub.yml ps

# View logs
docker-compose -f docker-compose.hub.yml logs -f web
docker-compose -f docker-compose.hub.yml logs -f bot
docker-compose -f docker-compose.hub.yml logs -f verifier
```

### Updates
```bash
# Pull latest images
docker-compose -f docker-compose.hub.yml pull

# Restart services with new images
docker-compose -f docker-compose.hub.yml up -d
```

### Backup
```bash
# Backup database
docker exec fundlink_postgres_1 pg_dump -U fundlink_prod fundlink_prod > backup.sql
```

## Quick Start Script

```bash
#!/bin/bash
# deploy.sh - Quick deployment script

set -e

DOCKER_USERNAME="yourusername"  # Replace with your username
DOMAIN="yourdomain.com"        # Replace with your domain

echo "Building and pushing Docker images..."
docker build --target web -t $DOCKER_USERNAME/fundlink-web:latest .
docker build --target bot -t $DOCKER_USERNAME/fundlink-bot:latest .  
docker build --target verifier -t $DOCKER_USERNAME/fundlink-verifier:latest .

docker push $DOCKER_USERNAME/fundlink-web:latest
docker push $DOCKER_USERNAME/fundlink-bot:latest
docker push $DOCKER_USERNAME/fundlink-verifier:latest

echo "Images pushed to Docker Hub successfully!"
echo "Update your docker-compose.hub.yml with:"
echo "  - image: $DOCKER_USERNAME/fundlink-web:latest"
echo "  - image: $DOCKER_USERNAME/fundlink-bot:latest" 
echo "  - image: $DOCKER_USERNAME/fundlink-verifier:latest"
echo ""
echo "Then deploy with:"
echo "docker-compose -f docker-compose.hub.yml --env-file .env.production up -d"
```

Would you like me to help you set up any specific part of this Docker Hub deployment process?