"""Intent agent that classifies user messages into structured intents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Optional

from .errors import LLMError
from .llm_client import complete

VALID_INTENTS = {
    "VIEW_CAMPAIGNS",
    "SELECT_CAMPAIGN",
    "DONATE",
    "HISTORY",
    "HELP",
    "UNKNOWN",
}

DEFAULT_INTENT = "UNKNOWN"
CONFIDENCE_FLOOR = 0.6


INTENT_SYSTEM_PROMPT = (
    "You are FundLink's Intent Agent for a Telegram donation bot on Avalanche Fuji.\n"
    "Classify the user's latest message into a donation intent.\n\n"
    "Rules:\n"
    "- Respond with STRICT JSON only (no prose).\n"
    "- Schema: {\"intent\": str, \"entities\": object, \"confidence\": float}.\n"
    "- Valid intents: VIEW_CAMPAIGNS, SELECT_CAMPAIGN, DONATE, HISTORY, HELP, UNKNOWN.\n"
    "- Entities may include campaign_id (int), campaign_title (str), amount (float), token ('AVAX'|'USDT').\n"
    "- Use token uppercase. If token unspecified, omit it.\n"
    "- Confidence must be 0.0–1.0. If unsure < 0.6, return intent UNKNOWN with empty entities.\n"
    "- If both campaign_title and campaign_id are known, include both.\n"
    "- Amount is the human amount the donor said (float).\n"
)

FEW_SHOTS = [
    {"role": "user", "content": "campaigns"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "VIEW_CAMPAIGNS",
                "entities": {},
                "confidence": 0.98,
            }
        ),
    },
    {"role": "user", "content": "donate 0.0001 to life"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "DONATE",
                "entities": {
                    "campaign_title": "life",
                    "amount": 0.0001,
                    "token": "AVAX",
                },
                "confidence": 0.92,
            }
        ),
    },
    {"role": "user", "content": "give 10 usdt to clean"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "DONATE",
                "entities": {
                    "campaign_title": "clean",
                    "amount": 10,
                    "token": "USDT",
                },
                "confidence": 0.90,
            }
        ),
    },
    {"role": "user", "content": "my donations"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "HISTORY",
                "entities": {},
                "confidence": 0.88,
            }
        ),
    },
]


@dataclass
class IntentPrediction:
    intent: str
    entities: Dict[str, Any]
    confidence: float
    raw: Dict[str, Any]


def _normalise_entities(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    entities: Dict[str, Any] = {}

    if "campaign_id" in payload:
        try:
            entities["campaign_id"] = int(payload["campaign_id"])
        except (TypeError, ValueError):
            pass

    if "campaign_title" in payload:
        title = payload.get("campaign_title")
        if isinstance(title, str) and title.strip():
            entities["campaign_title"] = title.strip()

    if "amount" in payload:
        try:
            entities["amount"] = float(payload["amount"])
        except (TypeError, ValueError):
            pass

    if "token" in payload:
        token = payload.get("token")
        if isinstance(token, str):
            token_upper = token.strip().upper()
            if token_upper in {"AVAX", "USDT"}:
                entities["token"] = token_upper

    if payload.get("detail") or payload.get("detail_request") or payload.get("show_detail"):
        entities["detail"] = True

    return entities


def _intent_from_raw(data: Dict[str, Any]) -> IntentPrediction:
    intent = str(data.get("intent", DEFAULT_INTENT)).strip().upper()
    if intent not in VALID_INTENTS:
        intent = DEFAULT_INTENT

    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    entities = _normalise_entities(data.get("entities", {}))

    if confidence < CONFIDENCE_FLOOR:
        intent = DEFAULT_INTENT
        entities = {}

    return IntentPrediction(intent=intent, entities=entities, confidence=confidence, raw=data)


async def classify_intent(
    user_text: str,
    *,
    user_state: Optional[Dict[str, Any]] = None,
) -> IntentPrediction:
    """Classify a user utterance into the bot intent schema."""

    if not user_text:
        return IntentPrediction(DEFAULT_INTENT, {}, 0.0, {"error": "empty"})

    lowered = user_text.strip().lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", lowered)
    tokens = [tok for tok in normalized.split() if tok]

    def _token_like(target: str, ratio: float = 0.8) -> bool:
        for tok in tokens:
            if tok == target:
                return True
            if SequenceMatcher(None, tok, target).ratio() >= ratio:
                return True
        return False

    has_about = _token_like("about") or "about" in lowered
    has_question = any(_token_like(option) for option in ["what", "whats", "what's", "wat"])
    has_tell = any(tok.startswith("tell") or tok.startswith("thell") or SequenceMatcher(None, tok, "tell").ratio() >= 0.75 for tok in tokens)
    has_detail_word = any(_token_like(option) for option in ["detail", "details"])
    has_more_info = "more info" in lowered or "more information" in lowered

    if has_about and (has_question or has_tell or has_detail_word or has_more_info):
        campaign = None
        campaign_id = None
        if user_state:
            campaign = user_state.get("current_campaign")
            if campaign and isinstance(campaign, dict):
                campaign_id = campaign.get("id")
            if not campaign_id:
                shown = user_state.get("last_shown_campaigns") or []
                if shown:
                    campaign = shown[0]
                    if isinstance(campaign, dict):
                        campaign_id = campaign.get("id")
        if campaign_id:
            return IntentPrediction(
                intent="SELECT_CAMPAIGN",
                entities={"campaign_id": int(campaign_id), "detail": True},
                confidence=0.9,
                raw={
                    "intent": "SELECT_CAMPAIGN",
                    "entities": {"campaign_id": campaign_id, "detail": True},
                    "heuristic": "detail",
                },
            )
        # No campaign in context yet – surface the campaign list so user can pick
        return IntentPrediction(
            intent="VIEW_CAMPAIGNS",
            entities={},
            confidence=0.7,
            raw={"intent": "VIEW_CAMPAIGNS", "entities": {}, "heuristic": "detail_no_context"},
        )

    messages = [{"role": "system", "content": INTENT_SYSTEM_PROMPT}]

    if user_state:
        parts = []
        campaign = user_state.get("current_campaign")
        if campaign and isinstance(campaign, dict):
            title = campaign.get("title")
            cid = campaign.get("id")
            if title and cid:
                parts.append(f"User was last viewing campaign '{title}' (id {cid}).")
        pending_token = user_state.get("pending_token")
        if pending_token:
            parts.append(f"Preferred token: {pending_token}.")
        if parts:
            messages.append({"role": "system", "content": "Context: " + " ".join(parts)})

    messages.extend(FEW_SHOTS)
    messages.append({"role": "user", "content": user_text})

    try:
        raw = await complete(messages, temperature=0.0, max_tokens=256)
    except LLMError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise LLMError(str(exc)) from exc

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("intent response is not an object")
    except Exception as exc:
        raise LLMError(f"Intent agent returned invalid JSON: {exc!s} :: {raw}") from exc

    return _intent_from_raw(data)


__all__ = ["classify_intent", "IntentPrediction", "VALID_INTENTS"]
