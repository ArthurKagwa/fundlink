from telbot_llm.deep_link import make_metamask_deep_link


def test_make_metamask_deep_link_avax():
    res = make_metamask_deep_link("0x1111111111111111111111111111111111111111", 0.5)
    assert res["token"] == "AVAX"
    assert res["deep_link"].startswith("https://link.metamask.io/send/0x1111")
    assert res["value_base_units"].isdigit()


def test_make_metamask_deep_link_token():
    usdt = "0x5425890298aed601595a70AB815c96711a31Bc65"
    res = make_metamask_deep_link("0x1111111111111111111111111111111111111111", 12.34, token=usdt, decimals=6)
    assert res["token"] == usdt
    assert "asset=" in res["deep_link"]
    assert res["value_base_units"].isdigit()


def test_make_metamask_deep_link_invalid():
    res = make_metamask_deep_link("bad", 1)
    assert res.get("error") == "invalid_address"
