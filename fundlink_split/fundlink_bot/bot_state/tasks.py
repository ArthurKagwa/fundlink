"""Celery tasks for bot state interactions."""

from __future__ import annotations

from celery import shared_task

from .models import IntentLog


@shared_task(bind=True)
def mark_intent_handled(self, intent_log_id: int) -> None:
    IntentLog.objects.filter(pk=intent_log_id).update(handled=True)
