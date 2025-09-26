import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from telbot_llm.handlers import get_user_state, handle_callback_query, handle_message
from telbot_llm.intent_agent import IntentPrediction
from telbot_llm.response_agent import AgentMessage, AgentResponse


def _dummy_update(message):
    return SimpleNamespace(message=message)


def _dummy_context():
    return SimpleNamespace()


@pytest.mark.asyncio
async def test_handle_message_dispatches_agent(monkeypatch):
    telegram_id = 999
    message = SimpleNamespace(
        text="campaigns",
        from_user=SimpleNamespace(id=telegram_id, username="tester"),
        reply_text=AsyncMock(),
    )

    monkeypatch.setattr("telbot_llm.handlers._USER_STATE", {})
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_CACHE", set())
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_ORDER", [])
    monkeypatch.setattr("telbot_llm.handlers.call_django_api", AsyncMock(return_value={"exists": True}))

    intent_prediction = IntentPrediction("VIEW_CAMPAIGNS", {}, 0.9, {})
    agent_response = AgentResponse(messages=[AgentMessage(text="Hi")])

    with patch("telbot_llm.handlers.classify_intent", new=AsyncMock(return_value=intent_prediction)) as mock_classify:
        with patch(
            "telbot_llm.handlers.response_handle_intent",
            new=AsyncMock(return_value=agent_response),
        ) as mock_response:
            await handle_message(_dummy_update(message), _dummy_context())

    mock_classify.assert_awaited()
    mock_response.assert_awaited()
    assert message.reply_text.await_count == 1


@pytest.mark.asyncio
async def test_handle_message_clears_state(monkeypatch):
    telegram_id = 321
    state = {
        "current_campaign_id": 12,
        "current_campaign": {"id": 12},
        "pending_amount": Decimal("0.1"),
        "pending_token": "USDT",
        "pending_decimals": 6,
        "last_used_token": "USDT",
        "last_shown_campaigns": [],
        "conversation_context": "donate",
    }
    message = SimpleNamespace(
        text="donate",
        from_user=SimpleNamespace(id=telegram_id, username="tester"),
        reply_text=AsyncMock(),
    )

    monkeypatch.setattr("telbot_llm.handlers._USER_STATE", {str(telegram_id): state})
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_CACHE", set())
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_ORDER", [])
    monkeypatch.setattr("telbot_llm.handlers.call_django_api", AsyncMock(return_value={"exists": True}))

    intent_prediction = IntentPrediction("DONATE", {"amount": 0.2}, 0.9, {})
    agent_response = AgentResponse(messages=[AgentMessage(text="Done")], clear_state=True)

    with patch("telbot_llm.handlers.classify_intent", new=AsyncMock(return_value=intent_prediction)):
        with patch(
            "telbot_llm.handlers.response_handle_intent",
            new=AsyncMock(return_value=agent_response),
        ):
            await handle_message(_dummy_update(message), _dummy_context())

    cleared = get_user_state(str(telegram_id))
    assert cleared["current_campaign_id"] is None
    assert cleared["current_campaign"] is None
    assert cleared["pending_amount"] is None
    assert cleared["pending_token"] == "USDT"


@pytest.mark.asyncio
async def test_handle_callback_query_routes_to_agent(monkeypatch):
    telegram_id = 555
    query = SimpleNamespace(
        data=json.dumps({"a": "history"}),
        from_user=SimpleNamespace(id=telegram_id),
        message=SimpleNamespace(reply_text=AsyncMock()),
        edit_message_text=AsyncMock(),
        answer=AsyncMock(),
    )

    monkeypatch.setattr("telbot_llm.handlers._USER_STATE", {})
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_CACHE", set())
    monkeypatch.setattr("telbot_llm.handlers._REGISTERED_USERS_ORDER", [])

    agent_response = AgentResponse(messages=[AgentMessage(text="History")])

    with patch(
        "telbot_llm.handlers.response_handle_callback",
        new=AsyncMock(return_value=agent_response),
    ) as mock_callback:
        await handle_callback_query(SimpleNamespace(callback_query=query), _dummy_context())

    mock_callback.assert_awaited()
    query.edit_message_text.assert_awaited()

