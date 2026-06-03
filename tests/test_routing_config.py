from techdoc_core.routing_config import DEFAULT_ROUTING, load_routing_config, parse_card_id


def test_default_routing_classifies_body_and_appendix():
    assert parse_card_id("1.1")[0] == "body"
    assert parse_card_id("3.4.2")[0] == "body"
    assert parse_card_id("A-1.4")[0] == "appendix"
    assert parse_card_id("D1.L2")[0] == "appendix"


def test_sort_key_orders_numerically():
    # 같은 part 내 정렬 키가 자연 정렬 가능해야
    a = parse_card_id("1.2")[1]
    b = parse_card_id("1.10")[1]
    assert a < b


def test_custom_config_overrides(tmp_path):
    cfg = tmp_path / "routing.json"
    cfg.write_text(
        '{"parts":[{"key":"crop","pattern":"^[RG]","dir":"Part-작물","label":"작물"}]}',
        encoding="utf-8")
    config = load_routing_config(cfg)
    assert parse_card_id("R1", config)[0] == "crop"
    assert parse_card_id("G1", config)[0] == "crop"


def test_unmatched_id_goes_to_misc():
    assert parse_card_id("???", DEFAULT_ROUTING)[0] == "misc"


def test_malformed_config_rejected_at_load(tmp_path):
    import pytest
    cfg = tmp_path / "bad.json"
    cfg.write_text('{"parts":[{"dir":"X","label":"X"}]}', encoding="utf-8")  # pattern·key 누락
    with pytest.raises(ValueError):
        load_routing_config(cfg)
