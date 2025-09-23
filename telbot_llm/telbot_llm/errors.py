class LLMError(Exception):
    """Raised for LLM client / model issues."""


class ToolExecutionError(Exception):
    """Raised when a backend tool call fails."""


class BackendAPIError(Exception):
    """Raised on non-2xx responses from backend API."""


__all__ = ["LLMError", "ToolExecutionError", "BackendAPIError"]