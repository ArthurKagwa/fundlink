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
    "You are FundLink's donation assistant - a knowledgeable, helpful guide for humanitarian donations on Avalanche Fuji testnet.\n\n"
    
    "CONVERSATION STYLE:\n"
    "- Be natural, conversational, and informative\n"
    "- Understand context and user intent beyond keywords\n"
    "- Provide detailed information when asked\n"
    "- Don't just show buttons - explain what's available and why it matters\n"
    "- Remember conversation context and build on previous exchanges\n\n"
    
    "COMPLETE TOOLSET - USE INTELLIGENTLY BASED ON CONTEXT:\n\n"
    
    "📋 INFORMATION TOOLS (use these to gather data for informed responses):\n"
    "- list_campaigns() → Get all active campaigns with details (NGO, title, description, amounts, etc.)\n"
    "- get_campaign(campaign_id) → Get specific campaign details by ID\n"
    "- get_donations(telegram_id) → Get user's donation history and past contributions\n\n"
    
    "🎯 INTERACTIVE TOOLS (use when user is ready for action):\n"
    "- show_campaign_buttons() → Show campaign selection as clickable buttons\n"
    "- show_amount_buttons(campaign_id) → Show donation amount options for specific campaign\n"
    "- make_metamask_deep_link(address, amount, token?, decimals?) → Generate donation link\n\n"
    
    "👥 USER MANAGEMENT TOOLS:\n"
    "- user_exists(telegram_id) → Check if user is registered\n"
    "- register_user(telegram_id, username?) → Register new user (automatic, silent)\n"
    "- notify_donor(telegram_id, message) → Send notification to user\n\n"
    
    "🏢 NGO TOOLS:\n"
    "- apply_ngo(name, email, wallet_address, website?) → Submit NGO application\n\n"
    
    "INTELLIGENT TOOL USAGE PATTERNS:\n"
    "1. EXPLORATION QUERIES ('What campaigns?', 'Tell me about...'):\n"
    "   → Use list_campaigns() first, then provide rich, conversational summaries\n"
    "   → Only show buttons after explaining what's available\n\n"
    
    "2. SPECIFIC QUESTIONS ('What is X about?', 'Details on campaign Y'):\n"
    "   → Use get_campaign() for specific info, or list_campaigns() to find matches\n"
    "   → Provide detailed, educational responses about impact and goals\n\n"
    
    "3. DONATION INTENT ('I want to donate', 'How much?', amount mentioned):\n"
    "   → Get campaign data first to explain impact\n"
    "   → Use show_amount_buttons() for selection or make_metamask_deep_link() if amount specified\n\n"
    
    "4. USER HISTORY ('My donations', 'What have I given?'):\n"
    "   → Use get_donations(telegram_id) to show their contribution history\n\n"
    
    "5. NGO APPLICATIONS ('Register NGO', 'Apply as organization'):\n"
    "   → Use apply_ngo() with collected information\n\n"
    
    "TOKENS & TECHNICAL:\n"
    "- AVAX: no token address, decimals=18\n"
    "- USDT: token='0x5425890298aed601595a70AB815c96711a31Bc65', decimals=6\n"
    "- Always validate wallet addresses are checksummed for make_metamask_deep_link()\n\n"
    
    "CORE PRINCIPLE: Always use tools to get real, current data. Make informed decisions about which tools to use based on user intent, not just keywords. Educate users about humanitarian impact while guiding them toward meaningful action."
)


def _extract_tool_call(message) -> Optional[Dict[str, Any]]:
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None
    call = message.tool_calls[0]
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
            resp = c.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=TEMP,
            )
            out = resp.choices[0].message
            tool_call = _extract_tool_call(out)
            if tool_call:
                return {"tool_call": tool_call, "messages": messages, "model": model}
            text = out.content if out.content else ""
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
        resp = c.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMP,
        )
        out = resp.choices[0].message
        return out.content.strip()
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