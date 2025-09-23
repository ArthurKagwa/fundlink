import os
import json
from typing import Any, Dict, List, Optional
from .tools import TOOLS
from .errors import LLMError

PRIMARY_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.1-70B-Instruct-Turbo")
FALLBACK_MODEL = os.getenv("TOGETHER_MODEL_FALLBACK", "meta-llama/Llama-3.1-8B-Instruct")
TEMP = float(os.getenv("LLM_TEMPERATURE", 0.2))
API_KEY = os.getenv("TOGETHER_API_KEY")

try:
    from together import Together
except ImportError:  # pragma: no cover
    Together = None  # type: ignore


def _client():
    if not API_KEY:
        raise LLMError("Missing TOGETHER_API_KEY")
    if Together is None:
        raise LLMError("together library not installed")
    return Together(api_key=API_KEY)


SYSTEM = (
    "You are FundLink's Telegram assistant. "
    "Answer concisely. Use tools for factual data (campaigns, donations, registration). "
    "Never fabricate blockchain transaction hashes, wallet addresses, or balances."
)


def _extract_tool_call(output_item) -> Optional[Dict[str, Any]]:
    if not hasattr(output_item, "tool_calls") or not output_item.tool_calls:
        return None
    call = output_item.tool_calls[0]
    raw_args = getattr(call.function, "arguments", {})
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            args = {}
    else:
        args = raw_args
    return {"name": call.function.name, "arguments": args}


async def chat_with_tools(user_text: str, telegram_id: str, history: Optional[List[Dict]] = None):
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    c = _client()
    last_err: Exception | None = None
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            resp = c.responses.create(
                model=model,
                input=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=TEMP,
            )
            out = resp.output[0]
            tool_call = _extract_tool_call(out)
            if tool_call:
                return {"tool_call": tool_call, "messages": messages, "model": model}
            text = out.content[0].text if out.content else ""
            return {"text": text.strip(), "messages": messages, "model": model}
        except Exception as e:  # pragma: no cover - network/model errors
            last_err = e
            continue
    raise LLMError(f"All model attempts failed: {last_err}")


async def continue_with_tool_result(state: Dict[str, Any], tool_result: Any):
    messages = list(state["messages"]) + [{"role": "tool", "content": _truncate(tool_result)}]
    c = _client()
    model = state.get("model", PRIMARY_MODEL)
    try:
        resp = c.responses.create(
            model=model,
            input=messages,
            temperature=TEMP,
        )
        out = resp.output[0]
        return out.content[0].text.strip()
    except Exception:  # pragma: no cover
        return f"Result: {_truncate(tool_result, 600)}"  # graceful degrade


def _truncate(payload: Any, limit: int = 800) -> str:
    try:
        if isinstance(payload, (dict, list)):
            return json.dumps(payload, ensure_ascii=False)[:limit]
        return str(payload)[:limit]
    except Exception:
        return "<unserializable>"


__all__ = [
    "chat_with_tools",
    "continue_with_tool_result",
]