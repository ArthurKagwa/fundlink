import pytest
from telbot_llm.tools import TOOLS

def test_tool_definitions():
    assert isinstance(TOOLS, list)
    assert len(TOOLS) > 0
    for wrapper in TOOLS:
        assert wrapper["type"] == "function"
        fn = wrapper["function"]
        assert {"name", "description", "parameters"}.issubset(fn.keys())
        assert fn["parameters"]["type"] == "object"

def _find(name: str):
    for w in TOOLS:
        if w["function"]["name"] == name:
            return w["function"]
    return None

def test_list_campaigns_tool():
    tool = _find("list_campaigns")
    assert tool is not None
    assert tool["function" if "function" in tool else "name"]  # placeholder sanity

def test_get_donations_tool():
    tool = _find("get_donations")
    assert tool is not None
    params = tool["parameters"]
    assert "telegram_id" in params["properties"]