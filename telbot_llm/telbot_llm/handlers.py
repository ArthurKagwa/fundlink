from __future__ import annotations

import json
import re
import time
from decimal import Decimal, InvalidOperation
from typing import Callable, Awaitable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .errors import BackendAPIError, LLMError, ToolExecutionError
from .intent_agent import classify_intent
from .response_agent import (
    AgentMessage,
    AgentResponse,
    ButtonSpec,
    handle_callback as response_handle_callback,
    handle_intent as response_handle_intent,
)
from .router import call_django_api

try:  # optional metrics
    from .telemetry.metrics import get_metrics
except Exception:  # pragma: no cover
    get_metrics = lambda: None  # type: ignore


_USER_STATE: dict[str, dict] = {}
_REGISTERED_USERS_CACHE: set[str] = set()
_REGISTERED_USERS_ORDER: list[str] = []


def get_user_state(telegram_id: str) -> dict:
    if telegram_id not in _USER_STATE:
        _USER_STATE[telegram_id] = {
            "current_campaign_id": None,
            "current_campaign": None,
            "pending_amount": None,
            "pending_token": "AVAX",
            "pending_decimals": 18,
            "last_used_token": "AVAX",
            "last_shown_campaigns": [],
            "conversation_context": "general",
            "last_acknowledged_donation_id": None,
            "last_confirmed_donation": None,
            "profile": {},
        }
    return _USER_STATE[telegram_id]


def clear_ephemeral_state(telegram_id: str):
    state = get_user_state(telegram_id)
    last_token = state.get("last_used_token", "AVAX")
    state.update(
        {
            "current_campaign_id": None,
            "current_campaign": None,
            "pending_amount": None,
            "pending_token": last_token,
            "pending_decimals": 18 if last_token == "AVAX" else 6,
        }
    )


_AMOUNT_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\b")


def extract_amount_from_text(text: str) -> Decimal | None:
    match = _AMOUNT_PATTERN.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1))
    except (InvalidOperation, ValueError):  # pragma: no cover - defensive
        return None


def extract_campaign_from_text(text: str, campaigns: list[dict]) -> dict | None:
    text_lower = text.lower()
    for campaign in campaigns:
        title = str(campaign.get("title", "")).lower()
        if title and title in text_lower:
            return campaign
    return None


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    started = time.perf_counter()
    metrics = get_metrics()
    if metrics:
        metrics.requests.inc()

    text = update.message.text.strip()
    telegram_id = str(update.message.from_user.id)
    username = getattr(update.message.from_user, "username", None)
    first_name = getattr(update.message.from_user, "first_name", None)
    last_name = getattr(update.message.from_user, "last_name", None)
    user_state = get_user_state(telegram_id)

    profile = user_state.setdefault("profile", {})
    if username:
        profile["username"] = username
    if first_name:
        profile["first_name"] = first_name
    if last_name:
        profile["last_name"] = last_name

    await _ensure_user_registered(telegram_id, username, first_name, last_name)

    try:
        intent = await classify_intent(text, user_state=user_state)
        response = await response_handle_intent(intent.intent, intent.entities, telegram_id, user_state)
        await _reply_with_agent_messages(update.message.reply_text, response)
        if response.clear_state:
            clear_ephemeral_state(telegram_id)
    except (LLMError, ToolExecutionError, BackendAPIError) as exc:
        await update.message.reply_text(f"Service issue: {exc}")
    except Exception:
        await update.message.reply_text("Unexpected error. Please try again shortly.")
    finally:
        if metrics:
            metrics.latency.observe(time.perf_counter() - started)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    telegram_id = str(query.from_user.id)
    user_state = get_user_state(telegram_id)

    try:
        payload = json.loads(query.data)
    except json.JSONDecodeError as exc:
        await query.edit_message_text(f"Button data invalid: {exc}")
        return

    action = payload.get("a")
    if not action:
        await query.edit_message_text("Unknown action.")
        return

    try:
        response = await response_handle_callback(action, payload, telegram_id, user_state)
        await _edit_or_send(query, response)
        if response.clear_state:
            clear_ephemeral_state(telegram_id)
    except (ToolExecutionError, BackendAPIError) as exc:
        await query.edit_message_text(f"Service issue: {exc}")
    except Exception:
        await query.edit_message_text("Unexpected error. Please try again later.")


async def _ensure_user_registered(
    telegram_id: str,
    username: str | None,
    first_name: str | None = None,
    last_name: str | None = None,
):
    if telegram_id in _REGISTERED_USERS_CACHE:
        return

    try:
        exists_resp = await call_django_api("user_exists", {"telegram_id": telegram_id})
        exists = bool(exists_resp.get("exists")) if isinstance(exists_resp, dict) else False
    except Exception:
        exists = False

    payload = {"telegram_id": telegram_id}
    if username:
        payload["username"] = username
    if first_name:
        payload["first_name"] = first_name
    if last_name:
        payload["last_name"] = last_name

    if not exists or len(payload) > 1:
        try:
            await call_django_api("register_user", payload)
        except Exception:
            pass

    _REGISTERED_USERS_CACHE.add(telegram_id)
    _REGISTERED_USERS_ORDER.append(telegram_id)
    if len(_REGISTERED_USERS_ORDER) > 10000:
        old = _REGISTERED_USERS_ORDER.pop(0)
        _REGISTERED_USERS_CACHE.discard(old)


async def _reply_with_agent_messages(
    sender: Callable[..., Awaitable],
    response: AgentResponse,
):
    for message in response.messages:
        keyboard = _keyboard_from_buttons(message.buttons)
        await sender(
            text=message.text,
            parse_mode=message.parse_mode,
            reply_markup=keyboard,
            disable_web_page_preview=message.disable_preview,
        )


async def _edit_or_send(query, response: AgentResponse):
    if not response.messages:
        return

    first = response.messages[0]
    keyboard = _keyboard_from_buttons(first.buttons)
    try:
        await query.edit_message_text(
            text=first.text,
            parse_mode=first.parse_mode,
            reply_markup=keyboard,
            disable_web_page_preview=first.disable_preview,
        )
    except Exception:
        await query.message.reply_text(
            text=first.text,
            parse_mode=first.parse_mode,
            reply_markup=keyboard,
            disable_web_page_preview=first.disable_preview,
        )

    for message in response.messages[1:]:
        keyboard = _keyboard_from_buttons(message.buttons)
        await query.message.reply_text(
            text=message.text,
            parse_mode=message.parse_mode,
            reply_markup=keyboard,
            disable_web_page_preview=message.disable_preview,
        )


def _keyboard_from_buttons(button_rows: list[list[ButtonSpec]] | None) -> InlineKeyboardMarkup | None:
    if not button_rows:
        return None
    rows: list[list[InlineKeyboardButton]] = []
    for row in button_rows:
        row_buttons: list[InlineKeyboardButton] = []
        for button in row:
            if button.url:
                row_buttons.append(InlineKeyboardButton(text=button.text, url=button.url))
            elif button.callback:
                row_buttons.append(
                    InlineKeyboardButton(
                        text=button.text,
                        callback_data=_encode_callback(button.callback),
                    )
                )
        if row_buttons:
            rows.append(row_buttons)
    return InlineKeyboardMarkup(rows) if rows else None


def _encode_callback(data: dict) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


__all__ = [
    "handle_message",
    "handle_callback_query",
    "get_user_state",
    "clear_ephemeral_state",
    "extract_amount_from_text",
    "extract_campaign_from_text",
]
