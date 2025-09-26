#!/bin/bash
# deploy-hub.sh - FundLink Docker Hub deployment script

set -e

# Configuration - CHANGE THESE VALUES
DOCKER_USERNAME="${DOCKER_USERNAME:-yourusername}"  # Replace with your Docker Hub username
IMAGE_TAG="${IMAGE_TAG:-latest}"
DOMAIN="${DOMAIN:-yourdomain.com}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 FundLink Docker Hub Deployment${NC}"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if logged into Docker Hub
if ! docker info | grep -q "Username:"; then
    echo -e "${YELLOW}⚠️  Not logged into Docker Hub. Please run 'docker login' first.${NC}"
    read -p "Do you want to login now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker login
    else
        echo -e "${RED}❌ Docker Hub login required. Exiting.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}📦 Building Docker images...${NC}"

# Build web service
echo "Building web service..."
docker build --target web -t $DOCKER_USERNAME/fundlink-web:$IMAGE_TAG .
echo -e "${GREEN}✅ Web service built${NC}"

# Build bot service
echo "Building bot service..."
docker build --target bot -t $DOCKER_USERNAME/fundlink-bot:$IMAGE_TAG .
echo -e "${GREEN}✅ Bot service built${NC}"

# Build verifier service
echo "Building verifier service..."
docker build --target verifier -t $DOCKER_USERNAME/fundlink-verifier:$IMAGE_TAG .
echo -e "${GREEN}✅ Verifier service built${NC}"

echo -e "${GREEN}📤 Pushing images to Docker Hub...${NC}"

# Push images
docker push $DOCKER_USERNAME/fundlink-web:$IMAGE_TAG
echo -e "${GREEN}✅ Web image pushed${NC}"

docker push $DOCKER_USERNAME/fundlink-bot:$IMAGE_TAG
echo -e "${GREEN}✅ Bot image pushed${NC}"

docker push $DOCKER_USERNAME/fundlink-verifier:$IMAGE_TAG
echo -e "${GREEN}✅ Verifier image pushed${NC}"

# Tag as latest if not already latest
if [ "$IMAGE_TAG" != "latest" ]; then
    echo -e "${GREEN}🏷️  Tagging as latest...${NC}"
    docker tag $DOCKER_USERNAME/fundlink-web:$IMAGE_TAG $DOCKER_USERNAME/fundlink-web:latest
    docker tag $DOCKER_USERNAME/fundlink-bot:$IMAGE_TAG $DOCKER_USERNAME/fundlink-bot:latest
    docker tag $DOCKER_USERNAME/fundlink-verifier:$IMAGE_TAG $DOCKER_USERNAME/fundlink-verifier:latest
    
    docker push $DOCKER_USERNAME/fundlink-web:latest
    docker push $DOCKER_USERNAME/fundlink-bot:latest
    docker push $DOCKER_USERNAME/fundlink-verifier:latest
    echo -e "${GREEN}✅ Latest tags pushed${NC}"
fi

echo
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=================================="
echo -e "📋 ${YELLOW}Next Steps:${NC}"
echo
echo "1. Create your production environment file:"
echo "   cp .env.example .env.production"
echo
echo "2. Update .env.production with your values:"
echo "   - POSTGRES_PASSWORD=your-secure-password"
echo "   - SECRET_KEY=your-django-secret-key"
echo "   - TELEGRAM_BOT_TOKEN=your-bot-token"
echo "   - TELEGRAM_WEBHOOK_URL=https://$DOMAIN/bot/api/webhook/telegram/"
echo "   - PUBLIC_WEBHOOK_BASE=https://$DOMAIN"
echo "   - ALLOWED_HOSTS=$DOMAIN,*.$DOMAIN"
echo "   - INTERNAL_API_KEY=your-secure-api-key"
echo
echo "3. Deploy with Docker Compose:"
echo "   DOCKER_USERNAME=$DOCKER_USERNAME IMAGE_TAG=$IMAGE_TAG docker-compose -f docker-compose.hub.yml --env-file .env.production up -d"
echo
echo "4. Set up SSL/HTTPS for your domain"
echo
echo "5. Test your deployment:"
echo "   - Web: https://$DOMAIN"
echo "   - Telegram bot webhook"
echo
echo -e "${GREEN}📦 Your images on Docker Hub:${NC}"
echo "   - $DOCKER_USERNAME/fundlink-web:$IMAGE_TAG"
echo "   - $DOCKER_USERNAME/fundlink-bot:$IMAGE_TAG"
echo "   - $DOCKER_USERNAME/fundlink-verifier:$IMAGE_TAG"
echo
echo -e "${YELLOW}💡 Pro tip: Set environment variables for easier deployment:${NC}"
echo "   export DOCKER_USERNAME=$DOCKER_USERNAME"
echo "   export IMAGE_TAG=$IMAGE_TAG"
echo "   export DOMAIN=$DOMAIN"