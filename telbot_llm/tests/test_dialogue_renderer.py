import pytest

from telbot_llm.dialogue_renderer import GeneratedMessage, generate_message


@pytest.mark.asyncio
async def test_generate_message_fallback(monkeypatch):
    async def boom(_):
        raise RuntimeError("fail")

    monkeypatch.setattr("telbot_llm.dialogue_renderer.complete", boom)

    result = await generate_message("help", {}, {"pending_token": "AVAX"})

    assert isinstance(result, GeneratedMessage)
    assert result.text
