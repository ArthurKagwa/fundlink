"""Definition of tool/function schemas passed to the Together API.

The structure follows the OpenAI / Together function calling spec:
tools = [
  {"type":"function","function":{"name":...,"description":...,"parameters":{...}}}, ...]
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_campaigns",
            "description": "Get list of active campaigns.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_campaign",
            "description": "Get campaign detail by id.",
            "parameters": {
                "type": "object",
                "properties": {"campaign_id": {"type": "integer"}},
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_donations",
            "description": "Get donation history for a Telegram user.",
            "parameters": {
                "type": "object",
                "properties": {"telegram_id": {"type": "string"}},
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_user",
            "description": "Register a Telegram user in the backend (idempotent).",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "string"},
                    "username": {"type": "string"},
                },
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "user_exists",
            "description": "Check if a Telegram user is already registered (lightweight).",
            "parameters": {
                "type": "object",
                "properties": {"telegram_id": {"type": "string"}},
                "required": ["telegram_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_donor",
            "description": "Send a donor a message via backend (secured).",
            "parameters": {
                "type": "object",
                "properties": {
                    "telegram_id": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["telegram_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_ngo",
            "description": "Submit NGO application payload.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "wallet_address": {"type": "string"},
                    "website": {"type": "string"},
                },
                "required": ["name", "email", "wallet_address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_campaign_buttons",
            "description": "Show interactive campaign selection buttons to user.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_option_buttons",
            "description": "Show custom option buttons for user choices (e.g., Learn more, Donate, History).",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message text to show with the buttons"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "Button text"},
                                "action": {"type": "string", "description": "Action type: 'campaign_detail', 'donate', 'history', 'campaigns'"},
                                "campaign_id": {"type": "integer", "description": "Campaign ID (if needed for action)"}
                            },
                            "required": ["text", "action"]
                        }
                    }
                },
                "required": ["message", "options"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_amount_buttons",
            "description": "Show amount selection buttons for a specific campaign.",
            "parameters": {
                "type": "object",
                "properties": {"campaign_id": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_metamask_deep_link",
            "description": "Create a MetaMask deep link for sending AVAX or an ERC20 token on Avalanche Fuji. Only use when user has specified both campaign and amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string", "description": "Recipient wallet address"},
                    "amount": {"type": "number", "description": "Human readable amount (e.g. 0.5)"},
                    "token": {"type": "string", "description": "ERC20 contract address (optional)"},
                    "decimals": {"type": "integer", "description": "Token decimals if token provided"},
                },
                "required": ["address", "amount"],
            },
        },
    },
]

__all__ = ["TOOLS"]