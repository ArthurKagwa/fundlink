"""Lightweight package init to avoid side-effect imports during partial tests.

Heavy modules (telegram, httpx) are imported lazily via accessors to prevent
test collection failures when only pure utility submodules are needed.
"""

from importlib import import_module


def _lazy(name: str):  # internal helper
	return import_module(f"telbot_llm.{name}")


def chat_with_tools(*a, **kw):  # type: ignore
	return _lazy("llm_client").chat_with_tools(*a, **kw)


def continue_with_tool_result(*a, **kw):  # type: ignore
	return _lazy("llm_client").continue_with_tool_result(*a, **kw)


def handle_message(*a, **kw):  # type: ignore
	return _lazy("handlers").handle_message(*a, **kw)


from .tools import TOOLS  # safe (data only)
from .errors import LLMError, ToolExecutionError, BackendAPIError  # lightweight

def call_django_api(*a, **kw):  # type: ignore
	return _lazy("router").call_django_api(*a, **kw)

__all__ = [
	"chat_with_tools",
	"continue_with_tool_result",
	"handle_message",
	"TOOLS",
	"call_django_api",
	"LLMError",
	"ToolExecutionError",
	"BackendAPIError",
]