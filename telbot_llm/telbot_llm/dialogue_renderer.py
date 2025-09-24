"""Generative renderer that crafts conversational messages using the LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import LLMError
from .llm_client import complete


@dataclass
class GeneratedMessage:
    text: str
    parse_mode: Optional[str] = "Markdown"


SYSTEM_PROMPT = (
    "You are the voice of FundLink, a Telegram bot helping donors support humanitarian campaigns on Avalanche Fuji.\n"
    "You will receive JSON with keys: event, payload, state.\n"
    'Respond with JSON: {"text": str, "parse_mode": "Markdown"|"HTML"|"Plain"}.\n'
    "Guidelines:\n"
    "- Keep language friendly, concise, and conversational.\n"
    "- Tailor tone to the event.\n"
    "- Invite the user to take the next step instead of giving directives.\n"
    "- Mention key figures (amounts, tokens) when available.\n"
    "- Refer to campaigns by title and NGO name.\n"
    "- When buttons are provided (e.g. amount suggestions), reference them naturally.\n"
    "- When event is 'donation_link', explain what the link does and remind about Avalanche Fuji network.\n"
    "- When event is 'view_campaigns', highlight a couple of campaigns and invite the user to pick one.\n"
    "- When event is 'campaign_detail', summarise the impact and suggest donating.\n"
    "- When event is 'amount_prompt', ask how much they'd like to give and hint at suggested buttons.\n"
    "- When event is 'history_empty', encourage making a first donation.\n"
    "- When event is 'history_list', recap recent donations appreciatively.\n"
    "- When event is 'help' or 'unknown', politely guide them toward available options.\n"
    "- Never invent campaign data beyond payload.\n"
)


FALLBACK_COPY = {
    "view_campaigns": "Here are some campaigns you can support right now.",
    "no_campaigns": "There aren't any live campaigns at the moment, but new ones launch soon!",
    "campaign_detail": "Here's a quick look at the campaign.",
    "amount_prompt": "How much would you like to contribute?",
    "min_amount_warning": "That amount is below the minimum for this campaign.",
    "donation_link": "Your MetaMask link is ready below—please confirm Avalanche Fuji is selected.",
    "history_empty": "Looks like you haven't donated yet. Ready to make your first impact?",
    "history_list": "Here are your latest donations—thank you!",
    "help": "I can show campaigns, donation history, or help you donate.",
    "unknown": "I didn't quite catch that. Want to see campaigns or your donation history?",
}


def _state_snapshot(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not state:
        return {}
    keys = [
        "pending_token",
        "last_used_token",
        "current_campaign_id",
        "conversation_context",
    ]
    return {k: state.get(k) for k in keys if k in state}


async def generate_message(event: str, payload: Dict[str, Any], user_state: Optional[Dict[str, Any]] = None) -> GeneratedMessage:
    """Return conversational copy for the given event using the LLM."""

    content = {
        "event": event,
        "payload": payload,
        "state": _state_snapshot(user_state),
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
    ]

    try:
        raw = await complete(messages)
    except (LLMError, Exception):
        return GeneratedMessage(text=FALLBACK_COPY.get(event, FALLBACK_COPY["unknown"]), parse_mode="Markdown")

    try:
        data = json.loads(raw)
        text = str(data.get("text", "")).strip()
        parse_mode = data.get("parse_mode") or "Markdown"
        if not text:
            raise ValueError("empty text")
        if parse_mode not in {"Markdown", "HTML", "Plain"}:
            parse_mode = "Markdown"
        return GeneratedMessage(text=text, parse_mode=None if parse_mode == "Plain" else parse_mode)
    except Exception:
        return GeneratedMessage(text=FALLBACK_COPY.get(event, FALLBACK_COPY["unknown"]), parse_mode="Markdown")


__all__ = ["GeneratedMessage", "generate_message"]
