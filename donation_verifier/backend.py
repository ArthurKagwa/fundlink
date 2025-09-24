from __future__ import annotations

from typing import Dict, List, Optional

import httpx


class BackendClient:
    """HTTP client for interacting with the FundLink backend."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 20.0):
        self.base_url = base_url.rstrip('/')
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

    def __enter__(self) -> "BackendClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
