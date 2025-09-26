from types import SimpleNamespace
from unittest.mock import patch

import pytest

from telbot_llm import llm_client


@pytest.mark.asyncio
async def test_complete_returns_text(monkeypatch):
    message = SimpleNamespace(content="{\"intent\": \"VIEW_CAMPAIGNS\"}")
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeChat:
        def __init__(self):
            self.completions = SimpleNamespace(create=lambda **_: response)

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    monkeypatch.setattr(llm_client, "Together", object())
    monkeypatch.setattr(llm_client, "API_KEY", "test-key")

    with patch("telbot_llm.llm_client._client", return_value=FakeClient()):
        out = await llm_client.complete([
            {"role": "user", "content": "hi"}
        ])

    assert out == message.content


@pytest.mark.asyncio
async def test_complete_raises_when_empty(monkeypatch):
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))])

    class FakeChat:
        def __init__(self):
            self.completions = SimpleNamespace(create=lambda **_: response)

    class FakeClient:
        def __init__(self):
            self.chat = FakeChat()

    monkeypatch.setattr(llm_client, "Together", object())
    monkeypatch.setattr(llm_client, "API_KEY", "test-key")

    with patch("telbot_llm.llm_client._client", return_value=FakeClient()):
        with pytest.raises(llm_client.LLMError):
            await llm_client.complete([{"role": "user", "content": "hi"}])
