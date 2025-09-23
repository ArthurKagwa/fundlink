#!/bin/bash

# Fundlink Telegram Bot Startup Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🤖 Starting Fundlink Telegram Bot...${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${RED}❌ Please configure your .env file with proper tokens and URLs${NC}"
    echo -e "${YELLOW}   Edit .env and add your TELEGRAM_BOT_TOKEN and BACKEND_URL${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${GREEN}📚 Installing dependencies...${NC}"
pip install -r requirements.txt

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check if bot token is configured
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" = "your_bot_token_here" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not configured in .env file${NC}"
    echo -e "${YELLOW}   Get your bot token from @BotFather on Telegram${NC}"
    exit 1
fi

# Check if backend URL is configured
if [ -z "$BACKEND_URL" ] || [ "$BACKEND_URL" = "http://localhost:8000" ]; then
    echo -e "${YELLOW}⚠️  Using default BACKEND_URL (http://localhost:8000)${NC}"
    echo -e "${YELLOW}   Make sure your Django backend is running on port 8000${NC}"
fi

# Determine run mode
if [ "$BOT_DEBUG" = "true" ]; then
    echo -e "${GREEN}🐛 Starting in development mode (polling)...${NC}"
    python bot.py
else
    echo -e "${GREEN}🚀 Starting in production mode (webhook)...${NC}"
    python webhook.py
fi