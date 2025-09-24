import pytest
from types import SimpleNamespace

from telbot_llm.response_agent import confirm_donation, AgentResponse


@pytest.mark.asyncio
async def test_confirm_donation_new_receipt(monkeypatch):
    user_state = {
        "last_acknowledged_donation_id": None,
        "profile": {"username": "tester", "first_name": "Test"},
    }

    donation = {
        "id": 77,
        "token": "AVAX",
        "amount_decimal": "0.100000",
        "campaign": {"title": "Flood Relief", "ngo": {"name": "Aid Org"}},
        "ngo": {"name": "Aid Org"},
        "explorer_url": "https://snowtrace.example/tx/123",
        "confirmed_at": "2024-01-01T00:00:00Z",
    }

    async def fake_call(tool_name, params):
        if tool_name == "get_donations":
            return {"results": [donation]}
        if tool_name == "register_user":
            return {"ok": True}
        raise AssertionError(f"unexpected tool {tool_name}")

    events = {}

    async def fake_generate(event, payload, user_state=None):
        events["event"] = event
        events["payload"] = payload
        return SimpleNamespace(text="receipt", parse_mode="Markdown")

    monkeypatch.setattr("telbot_llm.response_agent.call_django_api", fake_call)
    monkeypatch.setattr("telbot_llm.response_agent.generate_message", fake_generate)

    response = await confirm_donation("123", user_state)

    assert isinstance(response, AgentResponse)
    assert response.messages[0].text == "receipt"
    assert events["event"] == "donation_receipt"
    assert user_state["last_acknowledged_donation_id"] == 77
    assert user_state["last_confirmed_donation"]["campaign_title"] == "Flood Relief"


@pytest.mark.asyncio
async def test_confirm_donation_pending(monkeypatch):
    user_state = {"last_acknowledged_donation_id": None}

    async def fake_call(tool_name, params):
        if tool_name == "get_donations":
            return {"results": []}
        raise AssertionError(f"unexpected tool {tool_name}")

    events = {}

    async def fake_generate(event, payload, user_state=None):
        events["event"] = event
        return SimpleNamespace(text="pending", parse_mode="Markdown")

    monkeypatch.setattr("telbot_llm.response_agent.call_django_api", fake_call)
    monkeypatch.setattr("telbot_llm.response_agent.generate_message", fake_generate)

    response = await confirm_donation("123", user_state)

    assert response.messages[0].text == "pending"
    assert events["event"] == "receipt_pending"
    assert user_state.get("last_acknowledged_donation_id") is None


@pytest.mark.asyncio
async def test_confirm_donation_already_confirmed(monkeypatch):
    user_state = {"last_acknowledged_donation_id": 88}

    donation = {
        "id": 88,
        "token": "USDT",
        "amount_decimal": "5.000000",
        "campaign": {"title": "Shelter"},
        "ngo": {"name": "Relief"},
    }

    async def fake_call(tool_name, params):
        if tool_name == "get_donations":
            return [donation]
        raise AssertionError(f"unexpected tool {tool_name}")

    events = {}

    async def fake_generate(event, payload, user_state=None):
        events["event"] = event
        return SimpleNamespace(text="already", parse_mode="Markdown")

    monkeypatch.setattr("telbot_llm.response_agent.call_django_api", fake_call)
    monkeypatch.setattr("telbot_llm.response_agent.generate_message", fake_generate)

    response = await confirm_donation("123", user_state)

    assert response.messages[0].text == "already"
    assert events["event"] == "receipt_already_confirmed"
    assert user_state["last_acknowledged_donation_id"] == 88
*** End Patch
