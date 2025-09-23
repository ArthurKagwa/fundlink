import pytest
from unittest.mock import patch, AsyncMock
from telbot_llm import router


@pytest.mark.asyncio
async def test_call_django_api_list_campaigns(monkeypatch):
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"campaigns": []}
    client = AsyncMock()
    client.get.return_value = mock_resp
    async def _enter(*a, **k): return client
    async def _exit(*a, **k): return False
    mock_async_client = AsyncMock()
    mock_async_client.return_value.__aenter__.side_effect = _enter
    mock_async_client.return_value.__aexit__.side_effect = _exit
    monkeypatch.setattr(router, "httpx", type("HX", (), {"AsyncClient": mock_async_client}))
    res = await router.call_django_api("list_campaigns", {})
    assert res == {"campaigns": []}


@pytest.mark.asyncio
async def test_call_django_api_unknown_tool():
    res = await router.call_django_api("nope", {})
    assert res["error"].startswith("Unknown tool")