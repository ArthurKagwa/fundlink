"""
Configuration settings for Fundlink Telegram Bot
"""
import os
from typing import List, Dict

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('TELEGRAM_WEBHOOK_URL', '')

# Backend API Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')
# Unified internal service key
INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY', '')

# Avalanche Fuji Configuration
FUJI_CONFIG = {
    'chain_id': 43113,
    'rpc_url': 'https://api.avax-test.network/ext/bc/C/rpc',
    'explorer_url': 'https://testnet.snowtrace.io',
    'usdt_contract': '0x5425890298aed601595a70AB815c96711a31Bc65',
    'avax_decimals': 18,
    'usdt_decimals': 6
}

# Bot Settings
DEBUG = os.getenv('BOT_DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('BOT_LOG_LEVEL', 'INFO')

# Webhook Configuration
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '0.0.0.0')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))

# Donation Presets
DONATION_PRESETS = {
    'AVAX': ['0.01', '0.05', '0.1', '0.5', '1.0'],
    'USDT': ['1', '5', '10', '25', '50', '100']
}

# Message Templates
MESSAGES = {
    'welcome': (
        "🌟 Welcome to Fundlink, {name}!\n\n"
        "I help you donate AVAX or USDT to verified humanitarian organizations "
        "on the Avalanche Fuji testnet.\n\n"
        "Commands:\n"
        "/campaigns - Browse active campaigns\n"
        "/donate - Quick donate to a campaign\n"
        "/history - View your donation history\n"
        "/help - Show this help message"
    ),
    'no_campaigns': "No active campaigns available at the moment. Check back later!",
    'campaign_not_found': "Campaign not found or no longer active.",
    'donation_ready': (
        "🚀 **Ready to donate {amount} {token}**\n\n"
        "📍 Campaign: {campaign_title}\n"
        "🏢 NGO: {ngo_name}\n"
        "💳 Amount: {amount} {token}\n\n"
        "👆 Click the button below to open MetaMask and complete your donation.\n\n"
        "⏳ I'll notify you once the transaction is confirmed on-chain!"
    ),
    'no_history': (
        "You haven't made any donations yet.\n\n"
        "Use /campaigns to browse and donate to active campaigns!"
    ),
    'donation_confirmed': (
        "✅ **Donation Confirmed!**\n\n"
        "💰 Amount: {amount} {token}\n"
        "📍 Campaign: {campaign_title}\n"
        "🏢 NGO: {ngo_name}\n"
        "🔗 [View on Explorer]({explorer_url})\n\n"
        "Thank you for your contribution! 🙏"
    )
}

# API Endpoints
API_ENDPOINTS = {
    'campaigns': '/api/campaigns/',
    'campaign_detail': '/api/campaigns/{id}/',
    'donations': '/api/donations/',
    'user_register': '/api/bot/register-user/',
    'pending_donation': '/api/donations/pending/',
    'bot_notify': '/api/bot/notify/'
}

def get_api_url(endpoint: str, **kwargs) -> str:
    """Get full API URL for an endpoint."""
    path = API_ENDPOINTS[endpoint].format(**kwargs)
    return f"{BACKEND_URL}{path}"

def get_explorer_url(tx_hash: str) -> str:
    """Get explorer URL for a transaction."""
    return f"{FUJI_CONFIG['explorer_url']}/tx/{tx_hash}"