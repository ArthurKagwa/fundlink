"""
Command handlers for Fundlink Telegram Bot.
Handles /start, /campaigns, /history, /help commands.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
except ImportError:
    # Mock classes for testing without telegram installed
    Update = object
    InlineKeyboardButton = object
    InlineKeyboardMarkup = object
    ContextTypes = type('ContextTypes', (), {'DEFAULT_TYPE': object})

from handlers.base import BaseHandler
from config import MESSAGES


class CommandHandlers(BaseHandler):
    """Handles all bot commands."""
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        await self.log_user_action(user.id, 'start_command')
        
        try:
            # Register user with backend
            success = await self.api_client.register_user(user.id, user.username or '')
            if not success:
                self.logger.warning(f"Failed to register user {user.id}")
            
            welcome_text = MESSAGES['welcome'].format(name=user.first_name or 'there')
            await update.message.reply_text(welcome_text)
            
        except Exception as e:
            await self.handle_error(update, context, "Welcome! Something went wrong during setup, but you can still browse campaigns.")
    
    async def campaigns(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /campaigns and /donate commands."""
        user = update.effective_user
        await self.log_user_action(user.id, 'campaigns_command')
        
        try:
            campaigns = await self.api_client.get_campaigns()
            
            if not campaigns:
                await update.message.reply_text(MESSAGES['no_campaigns'])
                return
            
            keyboard = []
            for campaign in campaigns:
                button_text = f"{campaign['title']} - {campaign.get('ngo_name', 'Unknown NGO')}"
                callback_data = f"campaign_{campaign['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🎯 Active Campaigns:\n\nSelect a campaign to learn more and donate:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await self.handle_error(update, context, "Unable to load campaigns right now. Please try again later.")
    
    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /history command."""
        user = update.effective_user
        await self.log_user_action(user.id, 'history_command')
        
        try:
            donations = await self.api_client.get_user_donations(user.id)
            history_text = self.message_formatter.format_donation_history(donations)
            
            # Truncate if too long for Telegram
            if len(history_text) > 4096:
                history_text = history_text[:4093] + "..."
            
            await update.message.reply_text(history_text, parse_mode='Markdown')
            
        except Exception as e:
            await self.handle_error(update, context, "Unable to load your donation history. Please try again later.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        user = update.effective_user
        await self.log_user_action(user.id, 'help_command')
        
        help_text = (
            "🤖 **Fundlink Bot Help**\n\n"
            "**Commands:**\n"
            "/start - Welcome message and setup\n"
            "/campaigns - Browse active donation campaigns\n"
            "/donate - Quick donate (same as /campaigns)\n"
            "/history - View your donation history\n"
            "/help - Show this help message\n\n"
            "**How to donate:**\n"
            "1. Browse campaigns with /campaigns\n"
            "2. Select a campaign and donation amount\n"
            "3. Click 'Open MetaMask' to complete payment\n"
            "4. I'll confirm once your transaction is processed!\n\n"
            "**Supported tokens:**\n"
            "• AVAX (native Avalanche token)\n"
            "• USDT (testnet version)\n\n"
            "**Network:** Avalanche Fuji Testnet\n"
            "Need help? Contact our support team."
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')