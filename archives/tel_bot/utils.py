"""
Utility functions for the Fundlink Telegram Bot
"""
import logging
from typing import Dict, List, Optional
import requests
from config import BACKEND_URL, INTERNAL_API_KEY, FUJI_CONFIG, get_api_url, get_explorer_url

logger = logging.getLogger(__name__)

class APIClient:
    """Client for interacting with the Fundlink backend API."""
    
    def __init__(self):
        self.base_url = BACKEND_URL
        self.headers = {
            'Authorization': f'Bearer {INTERNAL_API_KEY}' if INTERNAL_API_KEY else '',
            'Content-Type': 'application/json'
        }
    
    async def register_user(self, telegram_id: int, username: str = '') -> bool:
        """Register or update user in backend."""
        try:
            data = {
                'telegram_id': telegram_id,
                'username': username,
                'last_seen_at': None  # Backend will set current timestamp
            }
            
            response = requests.post(
                get_api_url('user_register'),
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True
            else:
                logger.warning(f"Failed to register user {telegram_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering user {telegram_id}: {e}")
            return False
    
    async def get_campaigns(self) -> List[Dict]:
        """Fetch active campaigns from backend."""
        try:
            response = requests.get(
                get_api_url('campaigns'),
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', []) if isinstance(data, dict) else data
            else:
                logger.error(f"Failed to fetch campaigns: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching campaigns: {e}")
            return []
    
    async def get_campaign_detail(self, campaign_id: int) -> Optional[Dict]:
        """Fetch campaign details from backend."""
        try:
            response = requests.get(
                get_api_url('campaign_detail', id=campaign_id),
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch campaign {campaign_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching campaign {campaign_id}: {e}")
            return None
    
    async def get_user_donations(self, telegram_id: int) -> List[Dict]:
        """Fetch user's donation history from backend."""
        try:
            response = requests.get(
                get_api_url('donations'),
                params={'telegram_id': telegram_id},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', []) if isinstance(data, dict) else data
            else:
                logger.error(f"Failed to fetch donations for {telegram_id}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching donations for {telegram_id}: {e}")
            return []
    
    async def create_pending_donation(self, telegram_id: int, campaign_id: int, 
                                    token: str, amount: str) -> bool:
        """Create a pending donation record for tracking."""
        try:
            data = {
                'telegram_id': telegram_id,
                'campaign_id': campaign_id,
                'token': token,
                'amount': amount,
                'status': 'pending'
            }
            
            response = requests.post(
                get_api_url('pending_donation'),
                json=data,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return True
            else:
                logger.warning(f"Failed to create pending donation: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating pending donation: {e}")
            return False


class MetaMaskDeepLink:
    """Generate MetaMask deep links for donations."""
    
    @staticmethod
    def generate_link(to_address: str, token: str, amount: str) -> str:
        """Generate MetaMask deep link for donation."""
        if token == 'AVAX':
            # Convert AVAX to wei (18 decimals)
            amount_wei = int(float(amount) * (10 ** FUJI_CONFIG['avax_decimals']))
            return f"https://metamask.app.link/send/{to_address}?value={amount_wei}"
        elif token == 'USDT':
            # Convert USDT amount (6 decimals)
            amount_units = int(float(amount) * (10 ** FUJI_CONFIG['usdt_decimals']))
            return (
                f"https://metamask.app.link/send/{to_address}"
                f"?value={amount_units}&contractAddress={FUJI_CONFIG['usdt_contract']}"
            )
        else:
            raise ValueError(f"Unsupported token: {token}")


class MessageFormatter:
    """Format messages for Telegram."""
    
    @staticmethod
    def format_campaign_info(campaign: Dict) -> str:
        """Format campaign information for display."""
        info_text = (
            f"🎯 **{campaign['title']}**\n"
            f"🏢 {campaign.get('ngo_name', 'Unknown NGO')}\n\n"
            f"{campaign.get('description', 'No description available.')}\n\n"
        )
        
        if campaign.get('token_options'):
            info_text += f"💰 Accepted tokens: {', '.join(campaign['token_options'])}\n"
        
        if campaign.get('min_amount'):
            info_text += f"💵 Minimum: {campaign['min_amount']} tokens\n"
        
        return info_text
    
    @staticmethod
    def format_donation_history(donations: List[Dict]) -> str:
        """Format donation history for display."""
        if not donations:
            return "You haven't made any donations yet.\n\nUse /campaigns to browse and donate to active campaigns!"
        
        history_text = "📊 **Your Donation History**\n\n"
        
        for donation in donations:
            status_emoji = "✅" if donation.get('confirmed_at') else "⏳"
            history_text += (
                f"{status_emoji} {donation.get('amount', '?')} {donation.get('token', '?')}\n"
                f"📍 {donation.get('campaign_title') or 'Direct donation'}\n"
                f"🏢 {donation.get('ngo_name', 'Unknown NGO')}\n"
                f"📅 {donation.get('created_at', 'Unknown date')}\n"
            )
            
            if donation.get('tx_hash'):
                explorer_url = get_explorer_url(donation['tx_hash'])
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
        
        if donation.get('tx_hash'):
            explorer_url = get_explorer_url(donation['tx_hash'])
            receipt_text += f"🔗 [View on Explorer]({explorer_url})\n"
        
        receipt_text += "\nThank you for your contribution! 🙏"
        
        return receipt_text


def validate_amount(amount_str: str, token: str) -> bool:
    """Validate donation amount."""
    try:
        amount = float(amount_str)
        if amount <= 0:
            return False
        
        # Check reasonable limits
        if token == 'AVAX' and amount > 100:  # Max 100 AVAX
            return False
        elif token == 'USDT' and amount > 10000:  # Max 10k USDT
            return False
        
        return True
    except (ValueError, TypeError):
        return False


def truncate_text(text: str, max_length: int = 4096) -> str:
    """Truncate text to fit Telegram message limits."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."