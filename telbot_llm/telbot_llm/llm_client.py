import os
from typing import Dict, List, Optional

from .errors import LLMError

API_KEY = os.getenv("TOGETHER_API_KEY")
DEFAULT_MODEL = os.getenv(
    "INTENT_MODEL",
    os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
)
FALLBACK_MODEL = os.getenv(
    "INTENT_MODEL_FALLBACK",
    os.getenv("TOGETHER_MODEL_FALLBACK", "meta-llama/Llama-3.1-8B-Instruct"),
)
MODEL_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

try:  # pragma: no cover - exercised at runtime
    from together import Together
except ImportError:  # pragma: no cover
    Together = None  # type: ignore


def _client():
    """Return an authenticated Together client."""
    if not API_KEY:
        raise LLMError("Missing TOGETHER_API_KEY")
    if Together is None:
        raise LLMError("together library not installed")
    return Together(api_key=API_KEY)


def _candidate_models(preferred: Optional[str] = None) -> List[str]:
    """Build an ordered list of models to try without duplicates."""
    seen: set[str] = set()
    ordered: List[str] = []
    for name in (preferred, DEFAULT_MODEL, FALLBACK_MODEL):
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    if not ordered:
        raise LLMError("No model configured for Together API")
    return ordered


async def complete(
    messages: List[Dict[str, str]],
    *,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Execute a chat completion and return the assistant text.

    Retries the preferred model first, then falls back to configured defaults.
    """

    errors: List[str] = []
    for candidate in _candidate_models(model):
        try:
            client = _client()
            response = client.chat.completions.create(
                model=candidate,
                messages=messages,
                temperature=temperature if temperature is not None else MODEL_TEMPERATURE,
                max_tokens=max_tokens or MAX_TOKENS,
            )
            choice = response.choices[0].message if response.choices else None
            content = getattr(choice, "content", None)
            if not content:
                raise LLMError("Empty response from LLM")
            return content.strip()
        except Exception as exc:  # pragma: no cover - network/model failures
            errors.append(f"{candidate}: {exc}")
            continue

    raise LLMError("; ".join(errors) if errors else "LLM request failed")


__all__ = ["complete"]
