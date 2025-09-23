"""
Callback query handlers for Fundlink Telegram Bot.
Handles button clicks and inline interactions.
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
from config import MESSAGES, DONATION_PRESETS
from core.validators import validate_amount


class CallbackHandlers(BaseHandler):
    """Handles all callback queries (button clicks)."""
    
    async def campaign_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show campaign details and donation options."""
        query = update.callback_query
        await query.answer()
        
        try:
            campaign_id = int(query.data.split('_')[1])
            await self.log_user_action(query.from_user.id, 'view_campaign', {'campaign_id': campaign_id})
            
            campaign = await self.api_client.get_campaign_detail(campaign_id)
            
            if not campaign:
                await query.edit_message_text(MESSAGES['campaign_not_found'])
                return
            
            # Build campaign info text
            info_text = self.message_formatter.format_campaign_info(campaign)
            
            # Create donation amount buttons
            keyboard = []
            token_options = campaign.get('token_options', ['AVAX'])
            
            for token in token_options:
                amounts = DONATION_PRESETS.get(token, ['1'])
                
                for amount in amounts:
                    button_text = f"Donate {amount} {token}"
                    callback_data = f"donate_{campaign_id}_{token}_{amount}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # Add back button
            keyboard.append([InlineKeyboardButton("← Back to Campaigns", callback_data="back_campaigns")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await self.handle_error(update, context, "Unable to load campaign details. Please try again.")
    
    async def handle_donation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Generate MetaMask deep link for donation."""
        query = update.callback_query
        await query.answer()
        
        try:
            # Parse callback data: donate_campaignId_token_amount
            parts = query.data.split('_')
            campaign_id = int(parts[1])
            token = parts[2]
            amount = parts[3]
            
            await self.log_user_action(
                query.from_user.id, 
                'initiate_donation', 
                {'campaign_id': campaign_id, 'token': token, 'amount': amount}
            )
            
            # Validate amount
            if not validate_amount(amount, token):
                await query.edit_message_text("Invalid donation amount. Please try again.")
                return
            
            campaign = await self.api_client.get_campaign_detail(campaign_id)
            if not campaign:
                await query.edit_message_text(MESSAGES['campaign_not_found'])
                return
            
            # Generate MetaMask deep link
            ngo_wallet = campaign.get('ngo_wallet_address')
            if not ngo_wallet:
                await query.edit_message_text("NGO wallet address not configured.")
                return
            
            deep_link = self.api_client.deep_link_service.generate_link(ngo_wallet, token, amount)
            
            # Store pending donation (for tracking)
            await self.api_client.create_pending_donation(
                telegram_id=query.from_user.id,
                campaign_id=campaign_id,
                token=token,
                amount=amount
            )
            
            donation_text = MESSAGES['donation_ready'].format(
                amount=amount,
                token=token,
                campaign_title=campaign['title'],
                ngo_name=campaign.get('ngo_name', 'Unknown NGO')
            )
            
            keyboard = [
                [InlineKeyboardButton("🦊 Open MetaMask", url=deep_link)],
                [InlineKeyboardButton("← Back to Campaign", callback_data=f"campaign_{campaign_id}")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(donation_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await self.handle_error(update, context, "Unable to process donation request. Please try again.")
    
    async def back_to_campaigns(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle back to campaigns button."""
        query = update.callback_query
        await query.answer()
        
        try:
            await self.log_user_action(query.from_user.id, 'back_to_campaigns')
            
            campaigns = await self.api_client.get_campaigns()
            
            if not campaigns:
                await query.edit_message_text(MESSAGES['no_campaigns'])
                return
            
            keyboard = []
            for campaign in campaigns:
                button_text = f"{campaign['title']} - {campaign.get('ngo_name', 'Unknown NGO')}"
                callback_data = f"campaign_{campaign['id']}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🎯 Active Campaigns:\n\nSelect a campaign to learn more and donate:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await self.handle_error(update, context, "Unable to load campaigns. Please try again.")