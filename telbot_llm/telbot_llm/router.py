import os
from pathlib import Path
import httpx
from dotenv import load_dotenv
from .errors import BackendAPIError

# Ensure root .env is loaded (works when running outside Django context)
if not os.getenv("INTERNAL_API_KEY"):
    try:
        root_env = Path(__file__).resolve().parents[2] / '.env'
        if root_env.exists():
            load_dotenv(root_env)
            print(f"DEBUG - router loaded root .env from {root_env}")
    except Exception as e:  # non-fatal
        print(f"DEBUG - router failed to load root .env: {e}")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("INTERNAL_API_KEY", "")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", 20))

# Debug output for API key
print(f"DEBUG - Router loaded. API_KEY present: {bool(API_KEY)}")
print(f"DEBUG - BACKEND_URL: {BACKEND_URL}")

INTERNAL_HEADER_NAME = "X-INTERNAL-KEY"
SECURE_HEADERS = {INTERNAL_HEADER_NAME: API_KEY} if API_KEY else {}
_warned_missing_key = False


async def _check(resp: httpx.Response):
    if resp.status_code >= 400:
        snippet = resp.text[:300]
        raise BackendAPIError(f"Backend {resp.status_code}: {snippet}")
    ct = resp.headers.get("content-type", "")
    if "json" in ct:
        return resp.json()
    return resp.text


async def call_django_api(tool_name: str, params: dict):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        if tool_name == "list_campaigns":
            return await _check(await client.get(f"{BACKEND_URL}/api/campaigns/"))
        if tool_name == "get_campaign":
            campaign_id = params.get("campaign_id")
            return await _check(await client.get(f"{BACKEND_URL}/api/campaigns/{campaign_id}/"))
        if tool_name == "get_donations":
            return await _check(await client.get(f"{BACKEND_URL}/api/donations/", params=params))
        if tool_name == "user_exists":
            return await _check(
                await client.get(f"{BACKEND_URL}/api/bot/user-exists/", params=params, headers=SECURE_HEADERS)
            )
        if tool_name == "register_user":
            if not API_KEY:
                global _warned_missing_key
                if not _warned_missing_key:
                    print("WARN - INTERNAL_API_KEY not set; register_user will 401 against secured backend (missing X-INTERNAL-KEY)")
                    _warned_missing_key = True
            print(f"DEBUG - register_user tool called with headers: {SECURE_HEADERS}")
            return await _check(
                await client.post(
                    f"{BACKEND_URL}/api/bot/register-user/", json=params, headers=SECURE_HEADERS
                )
            )
        if tool_name == "notify_donor":
            return await _check(
                await client.post(
                    f"{BACKEND_URL}/api/bot/notify/", json=params, headers=SECURE_HEADERS
                )
            )
        if tool_name == "apply_ngo":
            print(f"DEBUG - apply_ngo tool called with headers: {SECURE_HEADERS}")
            return await _check(
                await client.post(f"{BACKEND_URL}/api/ngos/apply/", json=params, headers=SECURE_HEADERS)
            )
        if tool_name == "show_campaign_buttons":
            # This is handled directly in handlers.py, not a backend call
            return {"action": "show_campaigns"}
        if tool_name == "show_option_buttons":
            # This is handled directly in handlers.py, not a backend call
            return {"action": "show_options", "message": params.get("message", ""), "options": params.get("options", [])}
        if tool_name == "show_amount_buttons":
            # This is handled directly in handlers.py, not a backend call
            return {"action": "show_amounts", "campaign_id": params.get("campaign_id")}
        return {"error": f"Unknown tool {tool_name}"}


__all__ = ["call_django_api"]