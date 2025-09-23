import os
import httpx
from .errors import BackendAPIError

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("INTERNAL_API_KEY", "")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", 20))

SECURE_HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}


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
        if tool_name == "register_user":
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
            return await _check(
                await client.post(f"{BACKEND_URL}/api/ngos/apply/", json=params)
            )
        return {"error": f"Unknown tool {tool_name}"}


__all__ = ["call_django_api"]