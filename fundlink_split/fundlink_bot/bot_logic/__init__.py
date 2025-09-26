"""Lightweight package init to avoid side-effect imports during partial tests.

Heavy modules (telegram, httpx) are imported lazily via accessors to prevent
test collection failures when only pure utility submodules are needed.
"""

from __future__ import annotations

from importlib import import_module


def _lazy(name: str):
    return import_module(f"fundlink_bot.bot_logic.{name}")


def handle_message(*args, **kwargs):  # type: ignore
    return _lazy("handlers").handle_message(*args, **kwargs)


def handle_callback_query(*args, **kwargs):  # type: ignore
    return _lazy("handlers").handle_callback_query(*args, **kwargs)


def classify_intent(*args, **kwargs):  # type: ignore
    return _lazy("intent_agent").classify_intent(*args, **kwargs)


from .tools import TOOLS  # safe (data only)
from .errors import LLMError, ToolExecutionError, BackendAPIError  # lightweight


def call_django_api(*args, **kwargs):  # type: ignore
    return _lazy("router").call_django_api(*args, **kwargs)


__all__ = [
    "handle_message",
    "handle_callback_query",
    "classify_intent",
    "TOOLS",
    "call_django_api",
    "LLMError",
    "ToolExecutionError",
    "BackendAPIError",
]
