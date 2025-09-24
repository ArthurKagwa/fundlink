from unittest.mock import AsyncMock

import pytest

from telbot_llm.intent_agent import IntentPrediction, classify_intent


@pytest.mark.asyncio
async def test_classify_intent_detail_heuristic(monkeypatch):
    user_state = {
        "current_campaign": {"id": 7, "title": "Water"},
        "pending_token": "AVAX",
    }

    # Ensure we do not hit the LLM when heuristic matches
    monkeypatch.setattr("telbot_llm.intent_agent.complete", AsyncMock(side_effect=AssertionError("should not call")))

    result = await classify_intent("what is it about?", user_state=user_state)

    assert isinstance(result, IntentPrediction)
    assert result.intent == "SELECT_CAMPAIGN"
    assert result.entities["campaign_id"] == 7
    assert result.entities["detail"] is True


@pytest.mark.asyncio
async def test_detail_request_without_context_triggers_list(monkeypatch):
    monkeypatch.setattr("telbot_llm.intent_agent.complete", AsyncMock(side_effect=AssertionError("should not call")))

    result = await classify_intent("what are these things about?")

    assert result.intent == "VIEW_CAMPAIGNS"
    assert result.entities == {}


@pytest.mark.asyncio
async def test_detail_request_with_typo(monkeypatch):
    user_state = {
        "current_campaign": {"id": 42, "title": "Life"},
        "pending_token": "AVAX",
    }

    monkeypatch.setattr("telbot_llm.intent_agent.complete", AsyncMock(side_effect=AssertionError("should not call")))

    result = await classify_intent("what is it abouut", user_state=user_state)

    assert result.intent == "SELECT_CAMPAIGN"
    assert result.entities["campaign_id"] == 42
    assert result.entities["detail"] is True


@pytest.mark.asyncio
async def test_detail_request_with_thell(monkeypatch):
    user_state = {
        "current_campaign": None,
        "pending_token": "AVAX",
        "last_shown_campaigns": [
            {"id": 11, "title": "Life", "ngo_name": "Eco"},
            {"id": 12, "title": "Shelter", "ngo_name": "Relief"},
        ],
    }

    monkeypatch.setattr("telbot_llm.intent_agent.complete", AsyncMock(side_effect=AssertionError("should not call")))

    result = await classify_intent("Thell me about life by eco", user_state=user_state)

    assert result.intent == "SELECT_CAMPAIGN"
    assert result.entities["campaign_id"] == 11
    assert result.entities["detail"] is True
