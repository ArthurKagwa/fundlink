"""
Message formatting service for Telegram messages.
"""
from typing import Dict, List
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_explorer_url


class MessageFormatter:
    """Format messages for Telegram display."""
    
    @staticmethod
    def format_campaign_info(campaign: Dict) -> str:
        """Format campaign information for display."""
        title = campaign.get('title', 'Unknown Campaign')
        ngo_name = campaign.get('ngo_name', 'Unknown NGO')
        description = campaign.get('description', 'No description available.')
        
        info_text = (
            f"🎯 **{title}**\n"
            f"🏢 {ngo_name}\n\n"
            f"{description}\n\n"
        )
        
        # Add token options if available
        token_options = campaign.get('token_options')
        if token_options:
            info_text += f"💰 Accepted tokens: {', '.join(token_options)}\n"
        
        # Add minimum amount if specified
        min_amount = campaign.get('min_amount')
        if min_amount:
            info_text += f"💵 Minimum: {min_amount} tokens\n"
        
        # Add goal if available
        goal_amount = campaign.get('goal_amount')
        if goal_amount:
            info_text += f"🎯 Goal: {goal_amount} tokens\n"
        
        return info_text
    
    @staticmethod
    def format_donation_history(donations: List[Dict]) -> str:
        """Format donation history for display."""
        if not donations:
            return (
                "You haven't made any donations yet.\n\n"
                "Use /campaigns to browse and donate to active campaigns!"
            )
        
        history_text = "📊 **Your Donation History**\n\n"
        
        for donation in donations:
            # Status indicator
            status_emoji = "✅" if donation.get('confirmed_at') else "⏳"
            
            # Basic donation info
            amount = donation.get('amount', '?')
            token = donation.get('token', '?')
            campaign_title = donation.get('campaign_title') or 'Direct donation'
            ngo_name = donation.get('ngo_name', 'Unknown NGO')
            created_at = donation.get('created_at', 'Unknown date')
            
            history_text += (
                f"{status_emoji} {amount} {token}\n"
                f"📍 {campaign_title}\n"
                f"🏢 {ngo_name}\n"
                f"📅 {created_at}\n"
            )
            
            # Add explorer link if transaction hash exists
            tx_hash = donation.get('tx_hash')
            if tx_hash:
                explorer_url = get_explorer_url(tx_hash)
                history_text += f"🔗 [View on Explorer]({explorer_url})\n"
            
            history_text += "\n"
        
        return history_text
    
    @staticmethod
    def format_donation_receipt(donation: Dict) -> str:
        """Format donation confirmation receipt."""
        campaign_title = donation.get('campaign_title', 'Direct donation')
        ngo_name = donation.get('ngo_name', 'Unknown NGO')
        amount = donation.get('amount', '?')
        token = donation.get('token', '?')
        
        receipt_text = (
            f"✅ **Donation Confirmed!**\n\n"
            f"💰 Amount: {amount} {token}\n"
            f"📍 Campaign: {campaign_title}\n"
            f"🏢 NGO: {ngo_name}\n"
        )
        
        # Add explorer link if available
        tx_hash = donation.get('tx_hash')
        if tx_hash:
            explorer_url = get_explorer_url(tx_hash)
            receipt_text += f"🔗 [View on Explorer]({explorer_url})\n"
        
        receipt_text += "\nThank you for your contribution! 🙏"
        
        return receipt_text
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 4096) -> str:
        """Truncate text to fit Telegram message limits."""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."