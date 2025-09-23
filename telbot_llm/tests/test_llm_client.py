import pytest
from unittest.mock import patch
from telbot_llm import llm_client


@pytest.mark.asyncio
async def test_chat_with_tools_tool_call(monkeypatch):
    class FakeOut:
        def __init__(self):
            self.tool_calls = [type("TC", (), {"function": type("F", (), {"name": "list_campaigns", "arguments": "{}"})()})]
            self.content = [{"text": "Here are campaigns"}]
    class FakeResp:
        output = [FakeOut()]
    class FakeClient:
        class responses:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                return FakeResp()
    monkeypatch.setattr(llm_client, "Together", object())  # bypass import guard
    monkeypatch.setattr(llm_client, "API_KEY", "test")
    monkeypatch.setattr(llm_client, "_client", lambda: FakeClient())

    res = await llm_client.chat_with_tools("hi", "123")
    assert res["tool_call"]["name"] == "list_campaigns"


@pytest.mark.asyncio
async def test_continue_with_tool_result(monkeypatch):
    class FakeOut:
        def __init__(self):
            self.tool_calls = []
            self.content = [{"text": "Done"}]
    class FakeResp:
        output = [FakeOut()]
    class FakeClient:
        class responses:  # noqa: N801
            @staticmethod
            def create(**kwargs):
                return FakeResp()
    monkeypatch.setattr(llm_client, "Together", object())
    monkeypatch.setattr(llm_client, "API_KEY", "test")
    monkeypatch.setattr(llm_client, "_client", lambda: FakeClient())

    state = {"messages": [{"role": "user", "content": "hi"}], "model": "X"}
    txt = await llm_client.continue_with_tool_result(state, {"ok": True})
    assert txt == "Done"