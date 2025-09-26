"""Shared data contracts exchanged between FundLink services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class BotUserPayload:
    telegram_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }


@dataclass(slots=True)
class DonationIntentRequest:
    campaign_id: int
    token: str
    amount_decimal: str
    donor: BotUserPayload
    value_base_units: Optional[str] = None
    expires_in_minutes: int = 90
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "campaign_id": self.campaign_id,
            "token": self.token,
            "amount_decimal": self.amount_decimal,
            "expires_in_minutes": self.expires_in_minutes,
            "donor_telegram_id": self.donor.telegram_id,
            "telegram_username": self.donor.username,
            "telegram_first_name": self.donor.first_name,
            "telegram_last_name": self.donor.last_name,
        }
        if self.value_base_units is not None:
            payload["value_base_units"] = self.value_base_units
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload


@dataclass(slots=True)
class DonationNotification:
    telegram_id: str
    message_type: str
    message_data: Dict[str, Any]
    sent_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "telegram_id": self.telegram_id,
            "message_type": self.message_type,
            "message_data": self.message_data,
        }
        if self.sent_at:
            data["sent_at"] = self.sent_at.isoformat()
        return data


@dataclass(slots=True)
class CampaignSummary:
    id: int
    title: str
    ngo_name: str
    min_amount: str
    target_amount: Optional[str] = None

    @classmethod
    def from_api(cls, payload: Dict[str, Any]) -> "CampaignSummary":
        return cls(
            id=int(payload["id"]),
            title=str(payload.get("title", "")),
            ngo_name=str(payload.get("ngo_name", "")),
            min_amount=str(payload.get("min_amount", "")),
            target_amount=str(payload.get("target_amount")) if payload.get("target_amount") is not None else None,
        )


@dataclass(slots=True)
class IntentLogEntry:
    telegram_id: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    handled: bool = False
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "intent": self.intent,
            "entities": self.entities,
            "confidence": self.confidence,
            "handled": self.handled,
            "errors": self.errors,
        }


__all__ = [
    "BotUserPayload",
    "DonationIntentRequest",
    "DonationNotification",
    "CampaignSummary",
    "IntentLogEntry",
]
