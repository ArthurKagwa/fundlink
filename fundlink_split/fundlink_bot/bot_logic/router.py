"""Adapter that exposes backend actions to the bot runtime.

Historically the telbot package made direct httpx calls. This module now
proxies through the Django integration layer so everything flows via the
service's configured HTTP client and shared contracts.
"""

from __future__ import annotations

from typing import Any, Dict

from httpx import HTTPStatusError

from common import BotUserPayload, DonationIntentRequest, DonationNotification

from fundlink_bot.integrations import web_api
from .errors import BackendAPIError


async def call_django_api(tool_name: str, params: Dict[str, Any]) -> Any:
    try:
        if tool_name == "list_campaigns":
            return await web_api.list_campaigns()

        if tool_name == "get_campaign":
            campaign_id = params.get("campaign_id")
            if campaign_id is None:
                raise BackendAPIError("campaign_id is required")
            return await web_api.get_campaign(int(campaign_id))

        if tool_name == "get_donations":
            return await web_api.get_donations(params)

        if tool_name == "user_exists":
            telegram_id = params.get("telegram_id")
            if not telegram_id:
                raise BackendAPIError("telegram_id is required")
            return await web_api.user_exists(str(telegram_id))

        if tool_name == "register_user":
            telegram_id = params.get("telegram_id")
            if not telegram_id:
                raise BackendAPIError("telegram_id is required")
            payload = BotUserPayload(
                telegram_id=str(telegram_id),
                username=params.get("username"),
                first_name=params.get("first_name"),
                last_name=params.get("last_name"),
            )
            return await web_api.register_bot_user(payload)

        if tool_name == "create_donation_intent":
            donor_id = params.get("donor_telegram_id") or params.get("telegram_id")
            if donor_id is None:
                raise BackendAPIError("donor_telegram_id is required")
            donor_payload = BotUserPayload(
                telegram_id=str(donor_id),
                username=params.get("telegram_username"),
                first_name=params.get("telegram_first_name"),
                last_name=params.get("telegram_last_name"),
            )
            value_units = params.get("value_base_units")
            request = DonationIntentRequest(
                campaign_id=int(params["campaign_id"]),
                token=str(params["token"]),
                amount_decimal=str(params["amount_decimal"]),
                donor=donor_payload,
                value_base_units=str(value_units) if value_units is not None else None,
                metadata=params.get("metadata") or {},
            )
            return await web_api.ensure_intent(request)

        if tool_name == "notify_donor":
            telegram_id = params.get("telegram_id")
            message = params.get("message")
            if not telegram_id or not message:
                raise BackendAPIError("telegram_id and message are required")
            payload = DonationNotification(
                telegram_id=str(telegram_id),
                message_type="custom",
                message_data={"message": message},
            )
            return await web_api.notify_bot(payload)

        if tool_name == "apply_ngo":
            return await web_api.submit_ngo_application(params)

        if tool_name == "show_campaign_buttons":
            return {"action": "show_campaigns"}

        if tool_name == "show_option_buttons":
            return {
                "action": "show_options",
                "message": params.get("message", ""),
                "options": params.get("options", []),
            }

        if tool_name == "show_amount_buttons":
            return {
                "action": "show_amounts",
                "campaign_id": params.get("campaign_id"),
            }

        raise BackendAPIError(f"Unknown tool {tool_name}")

    except KeyError as exc:
        raise BackendAPIError(f"Missing required field: {exc}") from exc
    except HTTPStatusError as exc:  # normalised http errors
        raise BackendAPIError(str(exc)) from exc


__all__ = ["call_django_api"]
