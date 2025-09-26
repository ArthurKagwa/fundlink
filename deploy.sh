#!/bin/bash

# FundLink Deployment Script
# Usage: ./deploy.sh [platform] [environment]
# Platforms: render, railway, docker, fly
# Environments: dev, prod

set -e

PLATFORM=${1:-docker}
ENVIRONMENT=${2:-dev}

echo "🚀 Deploying FundLink to $PLATFORM ($ENVIRONMENT)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Source environment variables
source .env

# Validate required variables
check_env_var() {
    if [ -z "${!1}" ]; then
        echo "❌ Required environment variable $1 is not set"
        exit 1
    fi
}

echo "🔍 Validating environment variables..."
check_env_var SECRET_KEY
check_env_var INTERNAL_API_KEY

case $PLATFORM in
    "docker")
        echo "🐳 Deploying with Docker Compose..."
        if [ "$ENVIRONMENT" == "prod" ]; then
            check_env_var POSTGRES_PASSWORD
            docker-compose -f docker-compose.prod.yml build
            docker-compose -f docker-compose.prod.yml up -d
        else
            docker-compose build
            docker-compose up -d
        fi
        echo "✅ Docker deployment complete!"
        echo "📱 Web app: http://localhost:8000"
        ;;
        
    "render")
        echo "☁️ Deploying to Render..."
        check_env_var TELEGRAM_BOT_TOKEN
        check_env_var TOGETHER_API_KEY
        
        echo "1. Push your code to GitHub"
        echo "2. Connect repository to Render"
        echo "3. Deploy using render.yaml blueprint"
        echo "4. Configure these environment variables in Render dashboard:"
        echo "   - TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
        echo "   - TOGETHER_API_KEY=$TOGETHER_API_KEY"
        echo "   - TELEGRAM_WEBHOOK_URL=https://your-app.onrender.com/api/bot/webhook/"
        ;;
        
    "railway")
        echo "🚂 Deploying to Railway..."
        
        if ! command -v railway &> /dev/null; then
            echo "❌ Railway CLI not found. Install it first:"
            echo "npm install -g @railway/cli"
            exit 1
        fi
        
        # Deploy web service
        echo "🌐 Deploying web service..."
        railway login
        railway new fundlink-web --template postgres
        railway add postgresql
        railway up
        
        echo "✅ Web service deployed!"
        echo "🤖 To deploy bot and verifier, create separate Railway projects"
        ;;
        
    "fly")
        echo "🪰 Deploying to Fly.io..."
        
        if ! command -v flyctl &> /dev/null; then
            echo "❌ Fly CLI not found. Install it first:"
            echo "curl -L https://fly.io/install.sh | sh"
            exit 1
        fi
        
        echo "Creating Fly.io applications..."
        flyctl apps create fundlink-web --generate-name
        flyctl postgres create --name fundlink-db --region ord
        flyctl deploy --app fundlink-web
        
        echo "✅ Web service deployed to Fly.io!"
        ;;
        
    *)
        echo "❌ Unknown platform: $PLATFORM"
        echo "Supported platforms: docker, render, railway, fly"
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment process initiated for $PLATFORM!"
echo ""
echo "📋 Next steps:"
echo "1. Verify all services are running"
echo "2. Test Telegram bot functionality"  
echo "3. Check donation verification is working"
echo "4. Set up monitoring and alerts"
echo ""
echo "📖 For detailed instructions, see DEPLOYMENT.md"