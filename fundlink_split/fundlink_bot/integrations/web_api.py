"""HTTP client wrappers for communicating with fundlink_web."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, MutableMapping, Optional, Union

from django.conf import settings

from common import (
    BotUserPayload,
    DonationIntentRequest,
    DonationNotification,
    ServiceClient,
    ServiceClientConfig,
    get_json,
    post_json,
)

_client: ServiceClient | None = None


def get_client() -> ServiceClient:
    global _client
    if _client is None:
        config = ServiceClientConfig(
            base_url=settings.WEB_API_BASE_URL,
            api_key=settings.INTERNAL_API_KEY or None,
            timeout=float(getattr(settings, "HTTP_TIMEOUT", 20)),
        )
        _client = ServiceClient(config)
    return _client


def _as_payload(data: Union[BotUserPayload, DonationIntentRequest, DonationNotification, Mapping[str, Any]]) -> MutableMapping[str, Any]:
    if isinstance(data, (BotUserPayload, DonationIntentRequest, DonationNotification)):
        return data.to_dict()
    return dict(data)


async def list_campaigns() -> Any:
    return await get_json(get_client(), "/api/campaigns/")


async def get_campaign(campaign_id: int) -> Any:
    return await get_json(get_client(), f"/api/campaigns/{campaign_id}/")


async def donor_history(telegram_id: str) -> Any:
    return await get_json(get_client(), "/api/donations/", params={"telegram_id": telegram_id})


async def get_donations(params: Mapping[str, Any]) -> Any:
    return await get_json(get_client(), "/api/donations/", params=params)


async def user_exists(telegram_id: str) -> Any:
    return await get_json(get_client(), "/api/bot/user-exists/", params={"telegram_id": telegram_id})


async def register_bot_user(payload: Union[BotUserPayload, Mapping[str, Any]]) -> Any:
    return await post_json(get_client(), "/api/bot/register-user/", _as_payload(payload))


async def ensure_intent(request: Union[DonationIntentRequest, Mapping[str, Any]]) -> Any:
    return await post_json(get_client(), "/api/donations/intents/", _as_payload(request))


async def notify_bot(payload: Union[DonationNotification, Mapping[str, Any]]) -> Any:
    return await post_json(get_client(), "/api/bot/notify/", _as_payload(payload))


async def submit_ngo_application(payload: Mapping[str, Any]) -> Any:
    return await post_json(get_client(), "/api/ngos/apply/", dict(payload))


def close_client() -> None:
    global _client
    if _client is not None:
        asyncio.run(_client.close())
        _client = None


__all__ = [
    "list_campaigns",
    "get_campaign",
    "donor_history",
    "get_donations",
    "user_exists",
    "register_bot_user",
    "ensure_intent",
    "notify_bot",
    "submit_ngo_application",
    "close_client",
]
