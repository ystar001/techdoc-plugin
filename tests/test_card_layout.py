"""Plan D — card layout detection (F8) tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "cards"


def test_detect_mode_standard_when_writer_state_exists(tmp_path):
    from scripts.card_layout import detect_mode

    (tmp_path / "writer_state.json").write_text(
        json.dumps({"schema_version": "0.1.0", "section_states": {}}),
        encoding="utf-8",
    )
    assert detect_mode(tmp_path) == "standard"


def test_detect_mode_self_model_when_cards_dir_exists(tmp_path):
    from scripts.card_layout import detect_mode

    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "6.5_card.json").write_text(
        (FIXTURES / "self_model_layout.json").read_text("utf-8"),
        encoding="utf-8",
    )
    assert detect_mode(tmp_path) == "self_model"


def test_detect_mode_unknown_when_empty(tmp_path):
    from scripts.card_layout import detect_mode

    assert detect_mode(tmp_path) == "unknown"


def test_detect_mode_standard_takes_priority(tmp_path):
    """writer_state.json·cards/ 둘 다 있으면 standard 우선."""
    from scripts.card_layout import detect_mode

    (tmp_path / "writer_state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "cards").mkdir()
    (tmp_path / "cards" / "1.1_card.json").write_text("{}", encoding="utf-8")
    assert detect_mode(tmp_path) == "standard"


def test_load_self_model_card_returns_dict(tmp_path):
    from scripts.card_layout import load_self_model_card

    cards = tmp_path / "cards"
    cards.mkdir()
    src = (FIXTURES / "self_model_layout.json").read_text("utf-8")
    (cards / "6.5_card.json").write_text(src, encoding="utf-8")

    card = load_self_model_card(tmp_path, "6.5")
    assert card["id"] == "6.5"
    assert "sec1_definition_scope" in card["sections"]


def test_load_self_model_card_raises_when_missing(tmp_path):
    from scripts.card_layout import load_self_model_card

    with pytest.raises(FileNotFoundError):
        load_self_model_card(tmp_path, "9.9")


def test_load_standard_card_state_finds_card_in_writer_state(tmp_path):
    from scripts.card_layout import load_standard_card_state

    (tmp_path / "writer_state.json").write_text(
        json.dumps({
            "schema_version": "0.1.0",
            "section_states": {
                "1.1": {
                    "cards": [
                        {"id": "1.1.1", "type": "tech", "name": "X", "status": "completed"},
                        {"id": "1.1.2", "type": "tech", "name": "Y", "status": "completed"},
                    ],
                },
            },
        }),
        encoding="utf-8",
    )
    card = load_standard_card_state(tmp_path, "1.1.2")
    assert card["name"] == "Y"


def test_load_standard_card_state_raises_on_missing_id(tmp_path):
    from scripts.card_layout import load_standard_card_state

    (tmp_path / "writer_state.json").write_text(
        json.dumps({"section_states": {"1.1": {"cards": []}}}),
        encoding="utf-8",
    )
    with pytest.raises(KeyError):
        load_standard_card_state(tmp_path, "9.9.9")
