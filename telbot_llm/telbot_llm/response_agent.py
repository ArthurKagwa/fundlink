"""Deterministic response agent that turns intents into Telegram UI actions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Sequence

from .deep_link import make_metamask_deep_link
from .dialogue_renderer import generate_message
from .errors import BackendAPIError, ToolExecutionError
from .router import call_django_api


USDT_CONTRACT = "0x5425890298aed601595a70AB815c96711a31Bc65"
TOKEN_CONFIG = {
    "AVAX": {"token": None, "decimals": 18, "label": "AVAX"},
    "USDT": {"token": USDT_CONTRACT, "decimals": 6, "label": "USDT"},
}


@dataclass
class ButtonSpec:
    text: str
    callback: Optional[Dict[str, Any]] = None
    url: Optional[str] = None


@dataclass
class AgentMessage:
    text: str
    parse_mode: Optional[str] = None
    buttons: Optional[List[List[ButtonSpec]]] = None
    disable_preview: bool = True


@dataclass
class AgentResponse:
    messages: List[AgentMessage]
    clear_state: bool = False


async def handle_intent(
    intent: str,
    entities: Dict[str, Any],
    telegram_id: str,
    user_state: Dict[str, Any],
) -> AgentResponse:
    intent = intent.upper()

    if intent == "VIEW_CAMPAIGNS":
        return await view_campaigns(user_state)

    if intent == "SELECT_CAMPAIGN":
        campaign_id = entities.get("campaign_id")
        campaign_title = entities.get("campaign_title")
        detail_requested = bool(entities.get("detail") or entities.get("detail_request"))
        return await select_campaign(
            user_state,
            campaign_id=campaign_id,
            campaign_title=campaign_title,
            detail_requested=detail_requested,
        )

    if intent == "DONATE":
        return await donate_flow(user_state, entities)

    if intent == "HISTORY":
        return await show_history(telegram_id)

    if intent == "HELP":
        if entities.get("about_bot"):
            return await bot_info(user_state)
        if entities.get("out_of_scope"):
            return await out_of_scope(user_state)
        return await help_menu(user_state)

    return await unknown_menu(user_state)


async def view_campaigns(user_state: Dict[str, Any]) -> AgentResponse:
    campaigns = await _fetch_campaigns()
    if not campaigns:
        generated = await generate_message("no_campaigns", {}, user_state)
        return AgentResponse(messages=[AgentMessage(text=generated.text, parse_mode=generated.parse_mode, disable_preview=True)])

    user_state["last_shown_campaigns"] = [{"id": c.get("id"), "title": c.get("title", ""), "ngo_name": c.get("ngo_name", "")} for c in campaigns]
    generated = await generate_message(
        "view_campaigns",
        {
            "campaigns": [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "ngo_name": c.get("ngo_name"),
                    "min_amount": str(c.get("min_amount")),
                }
                for c in campaigns[:5]
            ]
        },
        user_state,
    )
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [
                ButtonSpec(
                    text=f"{c.get('title', 'Campaign')} — {c.get('ngo_name', '')}",
                    callback={"a": "sel", "c": c.get("id")},
                )
            ]
            for c in campaigns[:10]
        ],
    )
    user_state["conversation_context"] = "campaigns_shown"
    return AgentResponse(messages=[message])


async def select_campaign(
    user_state: Dict[str, Any], *, campaign_id: Optional[int] = None, campaign_title: Optional[str] = None, detail_requested: bool = False
) -> AgentResponse:
    campaign = None
    if campaign_id:
        campaign = await _fetch_campaign(campaign_id)
    if not campaign and campaign_title:
        campaign = await _resolve_campaign_by_title(campaign_title, user_state)

    if not campaign:
        return await view_campaigns(user_state)

    user_state["current_campaign_id"] = campaign.get("id")
    user_state["current_campaign"] = campaign

    preferred_token = user_state.get("pending_token") or "AVAX"
    preferred_token = _validate_token(preferred_token, campaign)
    user_state["pending_token"] = preferred_token
    user_state["pending_decimals"] = TOKEN_CONFIG[preferred_token]["decimals"]

    if detail_requested:
        user_state["conversation_context"] = "campaign_detail"
        description_text, description_quality = _prepare_description(campaign.get("description"))
        generated = await generate_message(
            "campaign_detail",
            {
                "title": campaign.get("title"),
                "ngo_name": campaign.get("ngo_name"),
                "description": description_text,
                "description_quality": description_quality,
                "min_amount": str(campaign.get("min_amount")),
                "target_amount": str(campaign.get("target_amount")),
            },
            user_state,
        )
        message = AgentMessage(
            text=generated.text,
            parse_mode=generated.parse_mode,
            buttons=[[ButtonSpec(text="💝 Donate", callback={"a": "donate", "c": campaign.get("id")})]],
        )
        return AgentResponse(messages=[message])

    generated = await generate_message(
        "amount_prompt",
        {
            "title": campaign.get("title"),
            "ngo_name": campaign.get("ngo_name"),
            "min_amount": str(campaign.get("min_amount")),
            "token": preferred_token,
        },
        user_state,
    )
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=_amount_buttons(campaign, preferred_token),
    )
    return AgentResponse(messages=[message])


async def donate_flow(user_state: Dict[str, Any], entities: Dict[str, Any]) -> AgentResponse:
    campaign = await _campaign_from_entities(user_state, entities)
    if not campaign:
        return await view_campaigns(user_state)

    amount_raw = entities.get("amount")
    amount = _to_decimal(amount_raw)

    token = entities.get("token") or user_state.get("pending_token") or "AVAX"
    token = _validate_token(token, campaign)
    user_state["pending_token"] = token
    user_state["pending_decimals"] = TOKEN_CONFIG[token]["decimals"]

    if amount is None:
        generated = await generate_message(
            "amount_prompt",
            {
                "title": campaign.get("title"),
                "ngo_name": campaign.get("ngo_name"),
                "min_amount": str(campaign.get("min_amount")),
                "token": token,
            },
            user_state,
        )
        return AgentResponse(
            messages=[
                AgentMessage(
                    text=generated.text,
                    parse_mode=generated.parse_mode,
                    buttons=_amount_buttons(campaign, token),
                )
            ]
        )

    min_amount = _to_decimal(campaign.get("min_amount")) or Decimal("0")
    if amount < min_amount:
        generated = await generate_message(
            "min_amount_warning",
            {
                "min_amount": str(min_amount),
                "token": token,
                "entered_amount": str(amount),
            },
            user_state,
        )
        return AgentResponse(
            messages=[
                AgentMessage(
                    text=generated.text,
                    parse_mode=generated.parse_mode,
                    buttons=_amount_buttons(campaign, token),
                )
            ]
        )

    wallet_address = _extract_wallet(campaign)
    if not wallet_address:
        raise ToolExecutionError("Campaign is missing a wallet address")

    token_cfg = TOKEN_CONFIG[token]
    deep_link = make_metamask_deep_link(
        address=wallet_address,
        amount=float(amount),
        token=token_cfg["token"],
        decimals=token_cfg["decimals"],
    )

    if "error" in deep_link:
        raise ToolExecutionError(f"Failed to build donation link: {deep_link['error']}")

    user_state["last_used_token"] = token

    campaign_title = campaign.get("title", "this campaign")
    generated = await generate_message(
        "donation_link",
        {
            "amount": str(amount),
            "token": token,
            "title": campaign_title,
        },
        user_state,
    )
    buttons = [
        [ButtonSpec(text="🦊 Donate with MetaMask", url=deep_link["deep_link"]),],
        [ButtonSpec(text="⬇️ Install MetaMask", callback={"a": "mmhelp"})],
        [ButtonSpec(text="➕ Add Avalanche Fuji", url="https://metamask.app.link/dapp/chainlist.org/chain/43113")],
    ]
    message = AgentMessage(text=generated.text, parse_mode=generated.parse_mode, buttons=buttons)
    return AgentResponse(messages=[message], clear_state=True)


async def show_history(telegram_id: str) -> AgentResponse:
    try:
        donations = await call_django_api("get_donations", {"telegram_id": telegram_id})
    except BackendAPIError as exc:
        raise ToolExecutionError(str(exc)) from exc

    donation_list: Sequence[Dict[str, Any]]
    if isinstance(donations, dict) and "results" in donations:
        donation_list = donations.get("results", [])
    elif isinstance(donations, list):
        donation_list = donations
    else:
        donation_list = []

    if not donation_list:
        generated = await generate_message("history_empty", {}, None)
        return AgentResponse(messages=[AgentMessage(text=generated.text, parse_mode=generated.parse_mode)])

    lines = []
    for donation in donation_list[:5]:
        amount = donation.get("amount", "0")
        token = donation.get("token", "AVAX")
        title = donation.get("campaign_title", "Campaign")
        created = donation.get("created_at", "")[:10]
        lines.append(f"• {amount} {token} → {title} ({created})")

    generated = await generate_message(
        "history_list",
        {
            "donations": lines,
        },
        None,
    )
    return AgentResponse(messages=[AgentMessage(text=generated.text, parse_mode=generated.parse_mode)])


async def help_menu(user_state: Optional[Dict[str, Any]] = None) -> AgentResponse:
    generated = await generate_message("help", {}, user_state)
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [ButtonSpec(text="📜 View Campaigns", callback={"a": "campaigns"})],
            [ButtonSpec(text="📋 My Donation History", callback={"a": "history"})],
        ],
    )
    return AgentResponse(messages=[message])


async def unknown_menu(user_state: Optional[Dict[str, Any]] = None) -> AgentResponse:
    generated = await generate_message("unknown", {}, user_state)
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [ButtonSpec(text="📜 Campaigns", callback={"a": "campaigns"})],
            [ButtonSpec(text="📋 My History", callback={"a": "history"})],
        ],
    )
    return AgentResponse(messages=[message])


async def bot_info(user_state: Optional[Dict[str, Any]] = None) -> AgentResponse:
    generated = await generate_message("bot_info", {}, user_state)
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [ButtonSpec(text="📜 View Campaigns", callback={"a": "campaigns"})],
            [ButtonSpec(text="📋 My Donation History", callback={"a": "history"})],
        ],
    )
    return AgentResponse(messages=[message])


async def out_of_scope(user_state: Optional[Dict[str, Any]] = None) -> AgentResponse:
    generated = await generate_message("out_of_scope", {}, user_state)
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [ButtonSpec(text="📜 Campaigns", callback={"a": "campaigns"})],
            [ButtonSpec(text="📋 My History", callback={"a": "history"})],
        ],
    )
    return AgentResponse(messages=[message])


async def metamask_help(user_state: Optional[Dict[str, Any]] = None) -> AgentResponse:
    generated = await generate_message("metamask_help", {}, user_state)
    message = AgentMessage(
        text=generated.text,
        parse_mode=generated.parse_mode,
        buttons=[
            [ButtonSpec(text="⬇️ MetaMask Mobile", url="https://metamask.app.link/download")],
            [ButtonSpec(text="🖥️ MetaMask Extension", url="https://metamask.io/download/")],
            [ButtonSpec(text="↩️ Back", callback={"a": "campaigns"})],
        ],
    )
    return AgentResponse(messages=[message])


async def handle_callback(
    action: str,
    data: Dict[str, Any],
    telegram_id: str,
    user_state: Dict[str, Any],
) -> AgentResponse:
    action = action.lower()

    if action == "sel":
        campaign_id = data.get("c")
        return await select_campaign(user_state, campaign_id=campaign_id)

    if action == "amt":
        campaign_id = data.get("c")
        value = data.get("v")
        entities = {"campaign_id": campaign_id, "amount": value}
        return await donate_flow(user_state, entities)

    if action == "tok":
        campaign_id = data.get("c")
        token = data.get("t")
        campaign = await _campaign_from_entities(user_state, {"campaign_id": campaign_id})
        if not campaign:
            return await view_campaigns(user_state)
        token = _validate_token(token or "AVAX", campaign)
        user_state["pending_token"] = token
        user_state["pending_decimals"] = TOKEN_CONFIG[token]["decimals"]
        generated = await generate_message(
            "amount_prompt",
            {
                "title": campaign.get("title"),
                "ngo_name": campaign.get("ngo_name"),
                "min_amount": str(campaign.get("min_amount")),
                "token": token,
            },
            user_state,
        )
        return AgentResponse(
            messages=[
                AgentMessage(
                    text=generated.text,
                    parse_mode=generated.parse_mode,
                    buttons=_amount_buttons(campaign, token),
                )
            ]
        )

    if action == "campaign_detail":
        campaign_id = data.get("c")
        campaign = await _campaign_from_entities(user_state, {"campaign_id": campaign_id})
        if not campaign:
            return await view_campaigns(user_state)
        description_text, description_quality = _prepare_description(campaign.get("description"))
        generated = await generate_message(
            "campaign_detail",
            {
                "title": campaign.get("title"),
                "ngo_name": campaign.get("ngo_name"),
                "description": description_text,
                "description_quality": description_quality,
                "min_amount": str(campaign.get("min_amount")),
                "target_amount": str(campaign.get("target_amount")),
            },
            user_state,
        )
        message = AgentMessage(
            text=generated.text,
            parse_mode=generated.parse_mode,
            buttons=[[ButtonSpec(text="💝 Donate", callback={"a": "donate", "c": campaign.get("id")})]],
        )
        return AgentResponse(messages=[message])

    if action == "donate":
        campaign_id = data.get("c")
        return await donate_flow(user_state, {"campaign_id": campaign_id})

    if action == "history":
        return await show_history(telegram_id)

    if action == "campaigns":
        return await view_campaigns(user_state)

    if action == "mmhelp":
        return await metamask_help(user_state)

    return await unknown_menu(user_state)


async def _fetch_campaigns() -> List[Dict[str, Any]]:
    try:
        campaigns = await call_django_api("list_campaigns", {})
    except BackendAPIError as exc:
        raise ToolExecutionError(str(exc)) from exc

    if isinstance(campaigns, dict) and "results" in campaigns:
        items = campaigns.get("results", [])
    elif isinstance(campaigns, list):
        items = campaigns
    else:
        items = []

    return [c for c in items if isinstance(c, dict)]


async def _fetch_campaign(campaign_id: Optional[int]) -> Optional[Dict[str, Any]]:
    if not campaign_id:
        return None
    try:
        data = await call_django_api("get_campaign", {"campaign_id": campaign_id})
    except BackendAPIError as exc:
        raise ToolExecutionError(str(exc)) from exc
    if isinstance(data, dict):
        return data
    return None


async def _resolve_campaign_by_title(title: str, user_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title_lower = title.lower().strip()
    candidates = user_state.get("last_shown_campaigns") or []
    if candidates:
        mapping = {c.get("title", "").lower(): c for c in candidates if isinstance(c, dict)}
        close = get_close_matches(title_lower, mapping.keys(), n=1, cutoff=0.4)
        if close:
            return await _fetch_campaign(mapping[close[0]].get("id"))

    campaigns = await _fetch_campaigns()
    mapping = {c.get("title", "").lower(): c for c in campaigns}
    close = get_close_matches(title_lower, mapping.keys(), n=1, cutoff=0.4)
    if close:
        return await _fetch_campaign(mapping[close[0]].get("id"))
    return None


async def _campaign_from_entities(user_state: Dict[str, Any], entities: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    campaign = None
    if entities.get("campaign_id"):
        try:
            campaign_id = int(entities["campaign_id"])
        except (TypeError, ValueError):
            campaign_id = None
        if campaign_id:
            campaign = await _fetch_campaign(campaign_id)
    if not campaign and entities.get("campaign_title"):
        campaign = await _resolve_campaign_by_title(str(entities["campaign_title"]), user_state)
    if not campaign:
        campaign = user_state.get("current_campaign")
    return campaign


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _validate_token(token: str, campaign: Dict[str, Any]) -> str:
    token_upper = (token or "AVAX").upper()
    options = campaign.get("token_options") or []
    options = [str(opt).upper() for opt in options if isinstance(opt, str)]
    if token_upper in options and token_upper in TOKEN_CONFIG:
        return token_upper
    if "AVAX" in options:
        return "AVAX"
    if options:
        for option in options:
            if option in TOKEN_CONFIG:
                return option
    return "AVAX"


def _amount_buttons(campaign: Dict[str, Any], token: str) -> List[List[ButtonSpec]]:
    min_amount = _to_decimal(campaign.get("min_amount")) or Decimal("0.0001")
    multiples = [min_amount, min_amount * 5, min_amount * 10]
    campaign_id = campaign.get("id")
    rows: List[List[ButtonSpec]] = []
    row: List[ButtonSpec] = []
    for amount in multiples:
        label = f"{_format_amount(amount)} {token}"
        row.append(ButtonSpec(text=label, callback={"a": "amt", "c": campaign_id, "v": str(amount)}))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    other = "USDT" if token == "AVAX" else "AVAX"
    rows.append([ButtonSpec(text=f"Switch to {other}", callback={"a": "tok", "c": campaign_id, "t": other})])
    return rows


def _prepare_description(raw: Any) -> tuple[str, str]:
    if not raw:
        return "", "missing"
    text = str(raw).strip()
    if not text:
        return "", "missing"
    words = text.split()
    if not words:
        return "", "missing"
    total = len(words)
    digit_words = sum(1 for w in words if any(ch.isdigit() for ch in w))
    non_alpha_chars = sum(1 for ch in text if not (ch.isalpha() or ch.isspace() or ch in "',.-"))
    letter_ratio = sum(1 for ch in text if ch.isalpha()) / max(len(text), 1)
    if letter_ratio < 0.5 or digit_words / total > 0.3 or non_alpha_chars / max(len(text), 1) > 0.15:
        return text, "noisy"
    return text, "ok"


def _format_amount(amount: Decimal) -> str:
    quantized = amount.normalize()
    return f"{quantized}".rstrip("0").rstrip(".") if "." in f"{quantized}" else f"{quantized}"


def _extract_wallet(campaign: Dict[str, Any]) -> Optional[str]:
    ngo = campaign.get("ngo")
    wallet = None
    if isinstance(ngo, dict):
        wallet = ngo.get("wallet_address")
    if not wallet:
        wallet = campaign.get("wallet_address")
    if isinstance(wallet, str) and wallet.startswith("0x") and len(wallet) == 42:
        return wallet
    return None


__all__ = [
    "AgentMessage",
    "AgentResponse",
    "ButtonSpec",
    "handle_intent",
    "handle_callback",
    "view_campaigns",
    "select_campaign",
    "donate_flow",
    "show_history",
    "help_menu",
    "unknown_menu",
    "bot_info",
    "out_of_scope",
    "metamask_help",
]
