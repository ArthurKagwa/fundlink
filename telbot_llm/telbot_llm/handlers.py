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

    # Silent registration (best-effort)
    try:
        await call_django_api(
            "register_user",
            {"telegram_id": tg_id, "username": update.message.from_user.username or ""},
        )
    except Exception:  # non-fatal
        pass

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