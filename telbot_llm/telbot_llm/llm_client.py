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
    "You are FundLink's donation assistant for humanitarian campaigns on Avalanche Fuji testnet.\n\n"
    
    "🚨 CRITICAL FUNCTION CALLING RULES:\n"
    "- ALWAYS call functions rather than mentioning them in text\n" 
    "- Functions are tools to be EXECUTED, not described\n"
    "- You can call multiple functions in sequence during a conversation\n"
    "- Provide natural, helpful responses along with function calls\n\n"
    
    "COMMON WORKFLOWS:\n"
    "1. When users ask about campaigns ('What campaigns', 'Hi', 'Show me campaigns'):\n"
    "   - First call list_campaigns() to get data\n"
    "   - Then call show_option_buttons() to show interactive options\n"
    "   - Provide friendly text about what's available\n\n"
    
    "2. When users want to donate or see details:\n"
    "   - Call appropriate functions (get_campaign, show_amount_buttons)\n"
    "   - Guide them through the process\n\n"
    
    "AVAILABLE FUNCTIONS (CALL THESE, DON'T MENTION THEM):\n"
    "- list_campaigns() → Get active campaigns\n" 
    "- show_option_buttons(message, options) → Show interactive buttons\n"
    "- get_donations(telegram_id) → Get user donation history\n"
    "- make_metamask_deep_link(address, amount, token?, decimals?) → Create donation link\n\n"
    
    "BUTTON OPTIONS FORMAT:\n"
    "When calling show_option_buttons(), use options like:\n"
    "[{text: '📖 Learn More', action: 'campaign_detail', campaign_id: 1},\n"
    " {text: '💝 Donate Now', action: 'donate', campaign_id: 1},\n"
    " {text: '📋 My History', action: 'history'}]\n\n"
    
    "RESPONSE STYLE:\n"
    "- Be friendly and conversational\n"
    "- Focus on humanitarian impact\n"
    "- Never show technical details or IDs to users\n"
    "- Always provide interactive elements when appropriate\n\n"
    
    "REMEMBER: Execute functions to create great user experiences!"
)


def _extract_tool_call(message) -> Optional[Dict[str, Any]]:
    """Extract the first tool call from a message"""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None
    
    # Debug: check if there are multiple tool calls
    if len(message.tool_calls) > 1:
        print(f"DEBUG - Multiple tool calls detected: {len(message.tool_calls)}")
        for i, call in enumerate(message.tool_calls):
            print(f"DEBUG - Tool call {i}: {call.function.name}")
    
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


def _extract_all_tool_calls(message) -> List[Dict[str, Any]]:
    """Extract all tool calls from a message"""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return []
    
    tool_calls = []
    for call in message.tool_calls:
        raw_args = getattr(call.function, "arguments", {})
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_args
        tool_calls.append({"name": call.function.name, "arguments": args})
    
    return tool_calls


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
            
            # Check for multiple tool calls
            all_tool_calls = _extract_all_tool_calls(out)
            if all_tool_calls:
                return {
                    "tool_calls": all_tool_calls,
                    "tool_call": all_tool_calls[0],  # Keep backward compatibility
                    "text": out.content.strip() if out.content else "",
                    "messages": messages, 
                    "model": model
                }
            
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
            tools=TOOLS,  # Enable tool calling in continuation
            tool_choice="auto",
            temperature=TEMP,
        )
        out = resp.choices[0].message
        
        # Check if the response contains a tool call
        tool_call = _extract_tool_call(out)
        if tool_call:
            return {"tool_call": tool_call, "text": out.content.strip() if out.content else "", "messages": messages, "model": model}
        
        return {"text": out.content.strip() if out.content else "", "messages": messages, "model": model}
    except Exception:  # pragma: no cover
        return {"text": f"Result: {_truncate(tool_result, 600)}", "messages": messages, "model": model}  # graceful degrade


def _truncate(payload: Any, limit: int = 800) -> str:
    """Clean and truncate tool results for LLM consumption"""
    try:
        if isinstance(payload, (dict, list)):
            # Convert to JSON but clean up for better LLM processing
            json_str = json.dumps(payload, ensure_ascii=False)
            
            # If it's campaign data, provide a cleaner summary for the LLM
            if isinstance(payload, dict):
                if 'results' in payload and isinstance(payload['results'], list):
                    # This is likely a paginated campaign response
                    campaigns = payload['results']
                    summary = f"Found {len(campaigns)} active campaign(s): "
                    for campaign in campaigns[:3]:  # Limit to 3 for brevity
                        title = campaign.get('title', 'Untitled')
                        ngo_name = campaign.get('ngo_name', 'Unknown NGO')
                        min_amount = campaign.get('min_amount', '0')
                        summary += f"'{title}' by {ngo_name} (min {min_amount} AVAX); "
                    return summary.rstrip('; ')
                elif 'title' in payload and 'ngo_name' in payload:
                    # Single campaign data
                    title = payload.get('title', 'Untitled')
                    ngo_name = payload.get('ngo_name', 'Unknown NGO')
                    description = payload.get('description', '').strip()
                    min_amount = payload.get('min_amount', '0')
                    target = payload.get('target_amount', '0')
                    return f"Campaign '{title}' by {ngo_name}. Description: {description[:100]}... Min donation: {min_amount} AVAX, Target: {target} AVAX"
            
            # For other data, truncate JSON
            return json_str[:limit]
        return str(payload)[:limit]
    except Exception:
        return "<data processing error>"


__all__ = [
    "chat_with_tools",
    "continue_with_tool_result",
]