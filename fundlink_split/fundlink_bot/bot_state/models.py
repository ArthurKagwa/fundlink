"""Database models for Telegram-facing state."""

from __future__ import annotations

from django.db import models


class BotUser(models.Model):
    telegram_id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bot_users"
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple repr
        return f"BotUser({self.telegram_id})"


class IntentLog(models.Model):
    telegram_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name="intent_logs")
    intent = models.CharField(max_length=64)
    entities = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0)
    handled = models.BooleanField(default=False)
    error_messages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bot_intent_logs"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["intent"]),
        ]


class ConversationState(models.Model):
    telegram_user = models.OneToOneField(BotUser, on_delete=models.CASCADE, related_name="conversation_state")
    state = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bot_conversation_state"


class MessageDelivery(models.Model):
    telegram_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name="deliveries")
    message_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bot_message_deliveries"
        indexes = [models.Index(fields=["status", "created_at"])]
