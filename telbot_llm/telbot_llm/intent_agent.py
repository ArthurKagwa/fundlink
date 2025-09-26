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
    "CONFIRM_DONATION",
    "GREETING",
    "DONATION_INTEREST",
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
    "- Valid intents: VIEW_CAMPAIGNS, SELECT_CAMPAIGN, DONATE, HISTORY, HELP, CONFIRM_DONATION, GREETING, DONATION_INTEREST, UNKNOWN.\n"
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
    {"role": "user", "content": "i successfully donated"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "CONFIRM_DONATION",
                "entities": {},
                "confidence": 0.9,
            }
        ),
    },
    {"role": "user", "content": "hi there"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "GREETING",
                "entities": {},
                "confidence": 0.82,
            }
        ),
    },
    {"role": "user", "content": "i'm feeling generous today"},
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "intent": "DONATION_INTEREST",
                "entities": {},
                "confidence": 0.86,
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

    greeting_keywords = ["hi", "hello", "hey", "hiya", "howdy", "heya", "greetings", "hola"]
    greeting_match = any(_token_like(keyword, 0.75 if len(keyword) > 3 else 1.0) for keyword in greeting_keywords)
    disqualify_tokens = {
        "donate",
        "donation",
        "campaign",
        "campaigns",
        "history",
        "help",
        "show",
        "view",
        "support",
    }
    if greeting_match:
        if len(tokens) <= 4 or not any(tok in disqualify_tokens for tok in tokens):
            return IntentPrediction(
                intent="GREETING",
                entities={},
                confidence=0.9,
                raw={"intent": "GREETING", "entities": {}, "heuristic": "greeting"},
            )

    generosity_phrases = [
        "feeling generous",
        "feelin generous",
        "feeling charitable",
        "in a giving mood",
        "give back",
        "ready to give",
        "ready to donate",
        "keen to donate",
        "keen to give",
        "want to give back",
        "want to help out",
    ]
    has_generous_word = "generous" in lowered or any(_token_like(word) for word in ["generous", "charitable", "giving"])
    has_feel_word = any(_token_like(word) for word in ["feel", "feeling", "felt"])
    has_ready_word = any(_token_like(word) for word in ["ready", "down", "keen"])
    has_support_word = any(_token_like(word) for word in ["give", "giving", "donate", "help", "support"])
    if any(phrase in lowered for phrase in generosity_phrases) or (
        has_generous_word and (has_feel_word or has_ready_word) and has_support_word
    ):
        return IntentPrediction(
            intent="DONATION_INTEREST",
            entities={},
            confidence=0.85,
            raw={"intent": "DONATION_INTEREST", "entities": {}, "heuristic": "donation_interest"},
        )

    has_about = _token_like("about") or "about" in lowered
    has_question = any(_token_like(option) for option in ["what", "whats", "what's", "wat"])
    has_tell = any(
        tok.startswith("tell")
        or tok.startswith("thell")
        or SequenceMatcher(None, tok, "tell").ratio() >= 0.75
        for tok in tokens
    )
    has_detail_word = any(_token_like(option) for option in ["detail", "details"])
    has_more_info = "more info" in lowered or "more information" in lowered
    pronoun_tokens = ["it", "its", "this", "that", "them", "they", "one", "these"]
    has_pronoun_reference = any(_token_like(pron, 0.7) for pron in pronoun_tokens)
    has_question_word = any(_token_like(word) for word in ["what", "when", "who", "where", "why", "how"])

    fundlink_terms = ["fundlink", "fund-link", "fund link"]
    mentions_fundlink = any(term in lowered for term in fundlink_terms) or _token_like("fundlink")
    if mentions_fundlink and (has_question_word or has_about or "info" in tokens or "information" in tokens):
        return IntentPrediction(
            intent="HELP",
            entities={"about_bot": True},
            confidence=0.85,
            raw={"intent": "HELP", "entities": {"about_bot": True}, "heuristic": "about_bot"},
        )

    def _match_campaign_from_tokens(candidates: list[Dict[str, Any]]) -> Optional[int]:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            cid = candidate.get("id")
            if not cid:
                continue
            title = str(candidate.get("title", "")).lower()
            parts = [part for part in re.split(r"\s+", title) if part]
            for part in parts:
                if any(SequenceMatcher(None, tok, part).ratio() >= 0.75 for tok in tokens):
                    try:
                        return int(cid)
                    except (TypeError, ValueError):
                        return None
        return None

    if has_about and (has_question or has_tell or has_detail_word or has_more_info):
        campaign = None
        campaign_id = None
        matched_campaign_id: Optional[int] = None
        if user_state:
            campaign = user_state.get("current_campaign")
            if campaign and isinstance(campaign, dict):
                try:
                    campaign_id = int(campaign.get("id"))
                except (TypeError, ValueError):
                    campaign_id = None

            candidates: list[Dict[str, Any]] = []
            last_shown = user_state.get("last_shown_campaigns") or []
            if isinstance(last_shown, list):
                candidates.extend([c for c in last_shown if isinstance(c, dict)])
            if campaign and isinstance(campaign, dict):
                candidates.append(campaign)

            matched_campaign_id = _match_campaign_from_tokens(candidates)
            if matched_campaign_id:
                campaign_id = matched_campaign_id

            if not campaign_id and has_pronoun_reference:
                if campaign and isinstance(campaign, dict):
                    try:
                        campaign_id = int(campaign.get("id"))
                    except (TypeError, ValueError):
                        campaign_id = None
                if not campaign_id and candidates:
                    first = candidates[0]
                    try:
                        campaign_id = int(first.get("id"))
                    except (TypeError, ValueError):
                        campaign_id = None

        if campaign_id and (matched_campaign_id or has_pronoun_reference):
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
        if has_pronoun_reference:
            return IntentPrediction(
                intent="VIEW_CAMPAIGNS",
                entities={},
                confidence=0.7,
                raw={"intent": "VIEW_CAMPAIGNS", "entities": {}, "heuristic": "detail_no_context"},
            )
        return IntentPrediction(
            intent="HELP",
            entities={"out_of_scope": True},
            confidence=0.65,
            raw={"intent": "HELP", "entities": {"out_of_scope": True}, "heuristic": "out_of_scope"},
        )

    yes_tokens = {"yes", "yeah", "yep", "ya", "yah", "sure", "ok", "okay", "affirmative"}
    if tokens and all(tok in yes_tokens for tok in tokens):
        if user_state:
            campaign = user_state.get("current_campaign")
            campaign_id = None
            if campaign and isinstance(campaign, dict):
                campaign_id = campaign.get("id")
            if not campaign_id:
                current_id = user_state.get("current_campaign_id")
                if current_id:
                    campaign_id = current_id
            if campaign_id:
                return IntentPrediction(
                    intent="DONATE",
                    entities={"campaign_id": int(campaign_id)},
                    confidence=0.85,
                    raw={"intent": "DONATE", "entities": {"campaign_id": campaign_id}, "heuristic": "affirmative"},
                )

    confirm_phrases = [
        "i donated",
        "i have donated",
        "i've donated",
        "i successfully donated",
        "donation complete",
        "donation is complete",
        "donation finished",
        "donation is done",
        "i finished my donation",
        "i completed the donation",
        "donation went through",
    ]
    confirmation_keywords = {
        "confirm",
        "confirmed",
        "confirmation",
        "receipt",
        "success",
        "successful",
        "successfully",
        "done",
        "complete",
        "completed",
        "finished",
        "received",
    }

    donation_mentioned = "donation" in lowered or "donated" in lowered or "donat" in lowered
    confirm_keyword_present = any(word in lowered for word in confirmation_keywords)
    confirm_phrase_present = any(phrase in lowered for phrase in confirm_phrases)

    if donation_mentioned and (confirm_keyword_present or confirm_phrase_present):
        return IntentPrediction(
            intent="CONFIRM_DONATION",
            entities={},
            confidence=0.9,
            raw={"intent": "CONFIRM_DONATION", "entities": {}, "heuristic": "confirm_donation"},
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
