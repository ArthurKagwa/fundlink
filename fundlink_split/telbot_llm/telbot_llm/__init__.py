"""Lightweight package init to avoid side-effect imports during partial tests.

Heavy modules (telegram, httpx) are imported lazily via accessors to prevent
test collection failures when only pure utility submodules are needed.
"""

from importlib import import_module


def _lazy(name: str):  # internal helper
	return import_module(f"telbot_llm.{name}")


def handle_message(*a, **kw):  # type: ignore
	return _lazy("handlers").handle_message(*a, **kw)


def handle_callback_query(*a, **kw):  # type: ignore
	return _lazy("handlers").handle_callback_query(*a, **kw)


def classify_intent(*a, **kw):  # type: ignore
	return _lazy("intent_agent").classify_intent(*a, **kw)


from .tools import TOOLS  # safe (data only)
from .errors import LLMError, ToolExecutionError, BackendAPIError  # lightweight

def call_django_api(*a, **kw):  # type: ignore
	return _lazy("router").call_django_api(*a, **kw)

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
