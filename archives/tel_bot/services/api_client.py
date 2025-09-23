"""
API Client service for Fundlink Telegram Bot.
Handles all communication with the backend API.
"""
import logging
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
except ImportError:
    requests = None
    logging.warning("requests not available")

from config import BACKEND_URL, INTERNAL_API_KEY, get_api_url
from services.deep_link import DeepLinkService

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the Fundlink backend API."""
    
    def __init__(self):
        self.base_url = BACKEND_URL
        self.headers = {
            'Authorization': f'Bearer {INTERNAL_API_KEY}' if INTERNAL_API_KEY else '',
            'Content-Type': 'application/json'
        }
        self.deep_link_service = DeepLinkService()
        self.timeout = 10
    
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
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully registered user {telegram_id}")
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
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                campaigns = data.get('results', []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(campaigns)} campaigns")
                return campaigns
            else:
                logger.error(f"Failed to fetch campaigns: {response.status_code} - {response.text}")
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
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                campaign = response.json()
                logger.info(f"Fetched campaign {campaign_id}: {campaign.get('title', 'Unknown')}")
                return campaign
            else:
                logger.error(f"Failed to fetch campaign {campaign_id}: {response.status_code} - {response.text}")
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
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                donations = data.get('results', []) if isinstance(data, dict) else data
                logger.info(f"Fetched {len(donations)} donations for user {telegram_id}")
                return donations
            else:
                logger.error(f"Failed to fetch donations for {telegram_id}: {response.status_code} - {response.text}")
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
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Created pending donation for user {telegram_id}: {amount} {token}")
                return True
            else:
                logger.warning(f"Failed to create pending donation: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating pending donation: {e}")
            return False