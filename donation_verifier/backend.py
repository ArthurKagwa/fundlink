from __future__ import annotations

from typing import Dict, List, Optional
import hashlib
import hmac
import json

import httpx


class BackendClient:
    """HTTP client for interacting with the FundLink backend."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 20.0, bot_notify_secret: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.bot_notify_secret = bot_notify_secret
        headers = {
            'X-INTERNAL-KEY': api_key,
            'Accept': 'application/json',
        }
        self._client = httpx.Client(timeout=timeout, headers=headers)

    def close(self) -> None:
        self._client.close()

    def list_intents(self, *, status: str = 'pending') -> List[Dict]:
        response = self._client.get(
            f"{self.base_url}/api/donations/intents/list/",
            params={'status': status},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get('results') if isinstance(payload, dict) else payload
        return items or []

    def confirm_donation(self, data: Dict) -> Dict:
        response = self._client.post(
            f"{self.base_url}/api/donations/confirm/",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    def register_intent(self, data: Dict) -> Dict:
        response = self._client.post(
            f"{self.base_url}/api/donations/intents/",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    def send_notification(self, telegram_id: int, message_type: str = 'donation_receipt', message_data: Optional[Dict] = None) -> Dict:
        """Send notification to Telegram user via bot integration endpoint using HMAC auth"""
        if not self.bot_notify_secret:
            raise ValueError('BOT_NOTIFY_SECRET not configured')
            
        payload = {
            'telegram_id': telegram_id,
            'message_type': message_type,
            'message_data': message_data or {}
        }
        
        payload_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        payload_bytes = payload_json.encode('utf-8')
        
        signature = hmac.new(
            self.bot_notify_secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'X-Signature': signature,
            'Content-Type': 'application/json',
        }
        
        response = httpx.post(
            f"{self.base_url}/api/bot/notify/",
            content=payload_bytes,
            headers=headers,
            timeout=self._client.timeout
        )
        response.raise_for_status()
        return response.json()

    def __enter__(self) -> "BackendClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
