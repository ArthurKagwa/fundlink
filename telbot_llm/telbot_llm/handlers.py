from telegram import Update
from telegram.ext import ContextTypes
import time
from .llm_client import chat_with_tools, continue_with_tool_result
from .router import call_django_api
from .deep_link import make_metamask_deep_link
from .errors import LLMError, BackendAPIError, ToolExecutionError

try:  # optional metrics
    from .telemetry.metrics import get_metrics
except Exception:  # pragma: no cover
    get_metrics = lambda: None  # type: ignore


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    started = time.perf_counter()
    metrics = get_metrics()
    if metrics:
        metrics.requests.inc()
    text = update.message.text.strip()
    tg_id = str(update.message.from_user.id)

    # Silent one-time registration (best-effort).
    # 1. Check local cache; if unknown, ask backend with lightweight GET; only POST if absent.
    global _REGISTERED_USERS_CACHE, _REGISTERED_USERS_ORDER
    if tg_id not in _REGISTERED_USERS_CACHE:
        try:
            exists_resp = await call_django_api("user_exists", {"telegram_id": tg_id})
            exists = bool(exists_resp.get("exists")) if isinstance(exists_resp, dict) else False
        except Exception:
            # If existence check fails (network, auth), optimistically try register (idempotent server-side)
            exists = False
        if not exists:
            try:
                await call_django_api(
                    "register_user",
                    {"telegram_id": tg_id, "username": update.message.from_user.username or ""},
                )
            except Exception:
                # Non-fatal; continue handling message
                pass
        _REGISTERED_USERS_CACHE.add(tg_id)
        _REGISTERED_USERS_ORDER.append(tg_id)
        if len(_REGISTERED_USERS_ORDER) > 10000:
            old = _REGISTERED_USERS_ORDER.pop(0)
            _REGISTERED_USERS_CACHE.discard(old)

    try:
        first = await chat_with_tools(text, tg_id)
        if first.get("tool_call"):
            tool = first["tool_call"]
            try:
                if tool["name"] == "make_metamask_deep_link":
                    result = make_metamask_deep_link(**tool["arguments"])
                else:
                    result = await call_django_api(tool["name"], tool["arguments"])
            except Exception as e:
                raise ToolExecutionError(str(e)) from e
            final_text = await continue_with_tool_result(first, result)
        else:
            final_text = first.get("text", "(no response)")
    except (LLMError, BackendAPIError, ToolExecutionError) as e:
        final_text = f"Service issue: {e}"
    except Exception:
        final_text = "Unexpected error. Please try again shortly."

    if metrics:
        metrics.latency.observe(time.perf_counter() - started)
    await update.message.reply_text(final_text, disable_web_page_preview=True)

__all__ = ["handle_message"]

# Module-level simple cache (declared after function to satisfy linters ordering preferences)
_REGISTERED_USERS_CACHE = set()
_REGISTERED_USERS_ORDER = []