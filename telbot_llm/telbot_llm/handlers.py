from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import time
import json
import re
from decimal import Decimal, InvalidOperation
from .llm_client import chat_with_tools, continue_with_tool_result
from .router import call_django_api
from .deep_link import make_metamask_deep_link
from .errors import LLMError, BackendAPIError, ToolExecutionError

try:  # optional metrics
    from .telemetry.metrics import get_metrics
except Exception:  # pragma: no cover
    get_metrics = lambda: None  # type: ignore


# In-memory conversation state (per telegram_id)
_USER_STATE = {}

def get_user_state(telegram_id: str) -> dict:
    """Get or create user conversation state"""
    if telegram_id not in _USER_STATE:
        _USER_STATE[telegram_id] = {
            'current_campaign_id': None,
            'current_campaign': None,
            'pending_amount': None,
            'pending_token': 'AVAX',
            'pending_decimals': 18,
            'last_used_token': 'AVAX'
        }
    return _USER_STATE[telegram_id]

def clear_ephemeral_state(telegram_id: str):
    """Clear ephemeral state after successful donation link generation"""
    if telegram_id in _USER_STATE:
        state = _USER_STATE[telegram_id]
        # Save the last used token before clearing
        last_token = state.get('pending_token', state.get('last_used_token', 'AVAX'))
        state.update({
            'current_campaign_id': None,
            'current_campaign': None,
            'pending_amount': None,
            'pending_token': last_token,
            'pending_decimals': 18 if last_token == 'AVAX' else 6,
            'last_used_token': last_token
        })


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    started = time.perf_counter()
    metrics = get_metrics()
    if metrics:
        metrics.requests.inc()
    
    text = update.message.text.strip()
    tg_id = str(update.message.from_user.id)

    # Silent one-time registration (best-effort)
    await _ensure_user_registered(tg_id, update.message.from_user.username)

    try:
        # Let LLM handle all conversation flow
        await _handle_with_llm(update, context, text, tg_id, started, metrics)
    
    except Exception as e:
        error_msg = f"Service issue: {e}" if isinstance(e, (LLMError, BackendAPIError, ToolExecutionError)) else "Unexpected error. Please try again shortly."
        await update.message.reply_text(error_msg, disable_web_page_preview=True)
        if metrics:
            metrics.latency.observe(time.perf_counter() - started)


async def _ensure_user_registered(tg_id: str, username: str | None):
    """Ensure user is registered in backend"""
    global _REGISTERED_USERS_CACHE, _REGISTERED_USERS_ORDER
    try:
        exists_resp = await call_django_api("user_exists", {"telegram_id": tg_id})
        exists = bool(exists_resp.get("exists")) if isinstance(exists_resp, dict) else False
    except Exception:
        exists = False
    
    if not exists:
        try:
            await call_django_api("register_user", {"telegram_id": tg_id, "username": username or ""})
        except Exception:
            pass  # Non-fatal
    
    _REGISTERED_USERS_CACHE.add(tg_id)
    _REGISTERED_USERS_ORDER.append(tg_id)
    if len(_REGISTERED_USERS_ORDER) > 10000:
        old = _REGISTERED_USERS_ORDER.pop(0)
        _REGISTERED_USERS_CACHE.discard(old)


async def _show_campaigns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available campaigns with buttons"""
    try:
        campaigns_response = await call_django_api("list_campaigns", {})
        
        # Handle paginated API response
        if isinstance(campaigns_response, dict) and 'results' in campaigns_response:
            campaigns = campaigns_response['results']
        elif isinstance(campaigns_response, list):
            campaigns = campaigns_response
        else:
            campaigns = []
        
        if not campaigns:
            await update.message.reply_text("No live campaigns yet.")
            return
        
        keyboard = []
        for campaign in campaigns[:10]:  # Limit to 10 campaigns
            title = campaign.get('title', 'Unknown')
            ngo_name = campaign.get('ngo_name', '')
            min_amount = campaign.get('min_amount', 0)
            button_text = f"{title} — {ngo_name} (min {min_amount} AVAX)"
            # Use shorter keys to reduce callback data size
            callback_data = json.dumps({"a": "sel", "c": campaign.get('id')})
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Here are live campaigns (pick one):", reply_markup=reply_markup)
    
    except Exception as e:
        await update.message.reply_text(f"Couldn't load campaigns: {e}")


async def _show_campaign_detail_with_amounts(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign: dict, user_state: dict):
    """Show campaign detail with amount selection buttons"""
    title = campaign.get('title', 'Campaign')
    ngo_name = campaign.get('ngo_name', '')
    min_amount = Decimal(str(campaign.get('min_amount', 0.0001)))
    target = campaign.get('target_amount', 0)
    campaign_id = campaign.get('id')
    
    # Create amount buttons
    keyboard = []
    
    # Suggested amounts
    amounts = [min_amount, min_amount * 5, min_amount * 10]
    amount_row = []
    for amount in amounts:
        if len(amount_row) >= 3:
            keyboard.append(amount_row)
            amount_row = []
        callback_data = json.dumps({"a": "amt", "c": campaign_id, "v": str(amount)})
        amount_row.append(InlineKeyboardButton(f"{amount} AVAX", callback_data=callback_data))
    
    if amount_row:
        keyboard.append(amount_row)
    
    # Token toggle button
    current_token = user_state.get('pending_token', 'AVAX')
    other_token = 'USDT' if current_token == 'AVAX' else 'AVAX'
    toggle_callback = json.dumps({"a": "tok", "c": campaign_id, "t": other_token})
    keyboard.append([InlineKeyboardButton(f"Switch to {other_token}", callback_data=toggle_callback)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"*{title}* — {ngo_name}\n"
        f"Min: {min_amount} AVAX • Target: {target} AVAX\n"
        f"Choose an amount:"
    )
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')


async def _handle_with_llm(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, tg_id: str, started: float, metrics):
    """Handle all conversation through LLM with proper tool execution"""
    try:
        first = await chat_with_tools(text, tg_id)
        
        if first.get("tool_call"):
            tool = first["tool_call"]
            result = None
            
            try:
                if tool["name"] == "make_metamask_deep_link":
                    # Generate deep link and show as button
                    result = make_metamask_deep_link(**tool["arguments"])
                    if isinstance(result, dict) and "deep_link" in result and not result.get("error"):
                        keyboard = [
                            [InlineKeyboardButton("🦊 Donate with MetaMask", url=result["deep_link"])],
                            [InlineKeyboardButton("➕ Add Avalanche Fuji Network", url="https://metamask.app.link/dapp/chainlist.org/chain/43113")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Extract donation details from tool arguments
                        amount = tool["arguments"].get("amount", "")
                        token_address = tool["arguments"].get("token")
                        token_symbol = "USDT" if token_address else "AVAX"
                        
                        message_text = (
                            f"Great! {amount} {token_symbol} donation ready\n\n"
                            f"⚠️ *Important*: Make sure MetaMask is connected to *Avalanche Fuji Testnet* (Chain ID: 43113)\n\n"
                            f"Tap to donate:"
                        )
                        await update.message.reply_text(
                            message_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        clear_ephemeral_state(tg_id)
                        return
                        
                elif tool["name"] == "show_campaign_buttons":
                    # Show campaigns as inline buttons
                    await _show_campaigns(update, context)
                    return
                    
                elif tool["name"] == "show_amount_buttons":
                    # Show amount selection buttons for a specific campaign
                    campaign_id = tool["arguments"].get("campaign_id")
                    if campaign_id:
                        try:
                            campaign = await call_django_api("get_campaign", {"campaign_id": campaign_id})
                            if isinstance(campaign, dict):
                                user_state = get_user_state(tg_id)
                                user_state['current_campaign_id'] = campaign_id
                                user_state['current_campaign'] = campaign
                                await _show_campaign_detail_with_amounts(update, context, campaign, user_state)
                                return
                        except Exception as e:
                            await update.message.reply_text(f"Error loading campaign: {e}")
                            return
                else:
                    # Regular API tool call
                    tool_args = tool["arguments"].copy()
                    
                    # Auto-inject telegram_id for user-specific tools
                    if tool["name"] in ["get_donations", "register_user", "notify_donor"] and "telegram_id" not in tool_args:
                        tool_args["telegram_id"] = tg_id
                    
                    result = await call_django_api(tool["name"], tool_args)
                    
            except Exception as e:
                raise ToolExecutionError(str(e)) from e
            
            # Continue conversation with tool result
            final_text = await continue_with_tool_result(first, result)
        else:
            # Direct LLM response
            final_text = first.get("text", "(no response)")
            
    except (LLMError, BackendAPIError, ToolExecutionError) as e:
        final_text = f"Service issue: {e}"
    except Exception:
        final_text = "Unexpected error. Please try again shortly."

    if metrics:
        metrics.latency.observe(time.perf_counter() - started)
    await update.message.reply_text(final_text, disable_web_page_preview=True)


async def _show_campaign_detail_with_amounts(update: Update, context: ContextTypes.DEFAULT_TYPE, campaign: dict, user_state: dict):
    """Show campaign detail with amount selection buttons"""
    title = campaign.get('title', 'Campaign')
    ngo_name = campaign.get('ngo_name', '')
    min_amount = Decimal(str(campaign.get('min_amount', 0.0001)))
    target = campaign.get('target_amount', 0)
    campaign_id = campaign.get('id')
    
    # Create amount buttons
    keyboard = []
    
    # Suggested amounts
    amounts = [min_amount, min_amount * 5, min_amount * 10]
    amount_row = []
    for amount in amounts:
        if len(amount_row) >= 3:
            keyboard.append(amount_row)
            amount_row = []
        callback_data = json.dumps({"a": "amt", "c": campaign_id, "v": str(amount)})
        amount_row.append(InlineKeyboardButton(f"{amount} AVAX", callback_data=callback_data))
    
    if amount_row:
        keyboard.append(amount_row)
    
    # Token toggle button
    current_token = user_state.get('pending_token', 'AVAX')
    other_token = 'USDT' if current_token == 'AVAX' else 'AVAX'
    toggle_callback = json.dumps({"a": "tok", "c": campaign_id, "t": other_token})
    keyboard.append([InlineKeyboardButton(f"Switch to {other_token}", callback_data=toggle_callback)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"*{title}* — {ngo_name}\n"
        f"Min: {min_amount} AVAX • Target: {target} AVAX\n"
        f"Choose an amount:"
    )
    
    await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button callbacks"""
    query = update.callback_query
    if not query or not query.data:
        return
    
    await query.answer()  # Acknowledge the callback
    
    try:
        data = json.loads(query.data)
        action = data.get("a")  # Shorter key
        tg_id = str(query.from_user.id)
        user_state = get_user_state(tg_id)
        
        if action == "sel":  # select_campaign
            await _handle_campaign_selection(query, context, data, user_state)
        elif action == "amt":  # donate_amount
            await _handle_amount_selection(query, context, data, tg_id, user_state)
        elif action == "tok":  # toggle_token
            await _handle_token_toggle(query, context, data, user_state)
        else:
            await query.edit_message_text(f"Unknown action: {action}")
    
    except json.JSONDecodeError as e:
        await query.edit_message_text(f"Button data invalid: {e}")
    except Exception as e:
        await query.edit_message_text(f"Error loading campaign: {e}")


async def _handle_campaign_selection(query, context: ContextTypes.DEFAULT_TYPE, data: dict, user_state: dict):
    """Handle campaign selection from inline button"""
    campaign_id = data.get("c")  # Shorter key
    if not campaign_id:
        await query.edit_message_text("Invalid campaign selection.")
        return
    
    try:
        campaign = await call_django_api("get_campaign", {"campaign_id": campaign_id})
        if not isinstance(campaign, dict):
            await query.edit_message_text("Campaign not found.")
            return
        
        # Update user state
        user_state['current_campaign_id'] = campaign_id
        user_state['current_campaign'] = campaign
        
        # Show amount selection buttons
        await _show_amount_buttons(query, context, campaign, user_state)
    
    except Exception as e:
        await query.edit_message_text(f"Error loading campaign: {e}")


async def _show_amount_buttons(query, context: ContextTypes.DEFAULT_TYPE, campaign: dict, user_state: dict):
    """Show amount selection buttons for a campaign"""
    title = campaign.get('title', 'Campaign')
    ngo_name = campaign.get('ngo_name', '')
    min_amount = Decimal(str(campaign.get('min_amount', 0.0001)))
    target = campaign.get('target_amount', 0)
    campaign_id = campaign.get('id')
    
    # Create amount buttons
    keyboard = []
    
    # Suggested amounts
    amounts = [min_amount, min_amount * 5, min_amount * 10]
    amount_row = []
    for amount in amounts:
        if len(amount_row) >= 3:
            keyboard.append(amount_row)
            amount_row = []
        callback_data = json.dumps({"a": "amt", "c": campaign_id, "v": str(amount)})
        amount_row.append(InlineKeyboardButton(f"{amount} AVAX", callback_data=callback_data))
    
    if amount_row:
        keyboard.append(amount_row)
    
    # Token toggle button
    current_token = user_state.get('pending_token', 'AVAX')
    other_token = 'USDT' if current_token == 'AVAX' else 'AVAX'
    toggle_callback = json.dumps({"a": "tok", "c": campaign_id, "t": other_token})
    keyboard.append([InlineKeyboardButton(f"Switch to {other_token}", callback_data=toggle_callback)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"*{title}* — {ngo_name}\n"
        f"Min: {min_amount} AVAX • Target: {target} AVAX\n"
        f"Choose an amount:"
    )
    
    await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')


async def _handle_amount_selection(query, context: ContextTypes.DEFAULT_TYPE, data: dict, tg_id: str, user_state: dict):
    """Handle amount selection and generate deep link"""
    campaign_id = data.get("c")  # Shorter key
    amount_str = data.get("v")  # Shorter key (value)
    
    if not campaign_id or not amount_str:
        await query.edit_message_text("Invalid amount selection.")
        return
    
    try:
        amount = Decimal(amount_str)
        campaign = user_state.get('current_campaign')
        
        if not campaign:
            # Fetch campaign if not in state
            campaign = await call_django_api("get_campaign", {"campaign_id": campaign_id})
            if not isinstance(campaign, dict):
                await query.edit_message_text("Campaign not found.")
                return
        
        # Generate deep link
        # Use NGO's wallet address for donations
        ngo = campaign.get('ngo', {})
        wallet_address = ngo.get('wallet_address')
        if not wallet_address:
            await query.edit_message_text("NGO wallet missing. Please contact support.")
            return
        
        token = user_state.get('pending_token', 'AVAX')
        decimals = 18 if token == 'AVAX' else 6
        token_contract = None if token == 'AVAX' else "0x5425890298aed601595a70AB815c96711a31Bc65"
        
        result = make_metamask_deep_link(
            address=wallet_address,
            amount=float(amount),
            token=token_contract,
            decimals=decimals
        )
        
        if "error" in result:
            await query.edit_message_text(f"Couldn't generate link: {result['error']}")
            return
        
        # Show donation button with network setup
        deep_link = result["deep_link"]
        keyboard = [
            [InlineKeyboardButton("🦊 Donate with MetaMask", url=deep_link)],
            [InlineKeyboardButton("➕ Add Avalanche Fuji Network", url="https://metamask.app.link/dapp/chainlist.org/chain/43113")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        campaign_title = campaign.get('title', 'Campaign')
        message_text = (
            f"Great! {amount} {token} to *{campaign_title}*\n\n"
            f"⚠️ *Important*: Make sure MetaMask is connected to *Avalanche Fuji Testnet* (Chain ID: 43113)\n\n"
            f"Tap to donate:"
        )
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Clear ephemeral state
        clear_ephemeral_state(tg_id)
    
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


async def _handle_token_toggle(query, context: ContextTypes.DEFAULT_TYPE, data: dict, user_state: dict):
    """Handle token toggle (AVAX <-> USDT)"""
    new_token = data.get("t", 'AVAX')  # Shorter key (token)
    campaign_id = data.get("c")  # Shorter key
    
    user_state['pending_token'] = new_token
    user_state['pending_decimals'] = 18 if new_token == 'AVAX' else 6
    user_state['last_used_token'] = new_token
    
    # Refresh the campaign selection with new token
    try:
        campaign = await call_django_api("get_campaign", {"campaign_id": campaign_id})
        if isinstance(campaign, dict):
            await _show_amount_buttons(query, context, campaign, user_state)
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")


__all__ = ["handle_message", "handle_callback_query"]

# Module-level simple cache (declared after function to satisfy linters ordering preferences)
_REGISTERED_USERS_CACHE = set()
_REGISTERED_USERS_ORDER = []