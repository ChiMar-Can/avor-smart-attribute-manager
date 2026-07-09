"""Tests für das Laden des Regelwerks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from avor_smart_attribute_manager.rules.attribute_rules import (
    InvalidRulesError,
    load_attribute_rules,
)


def _write_rules(path: Path, data: dict[str, object]) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_bundled_default_rules() -> None:
    rules = load_attribute_rules()

    # Das mitgelieferte Standard-Regelwerk ist leer und muss befüllt werden.
    assert rules.known_sachgruppen == frozenset()


def test_load_custom_rules_from_path(tmp_path: Path) -> None:
    rules_path = _write_rules(
        tmp_path / "rules.json",
        {
            "version": 1,
            "sachgruppen": {
                "WIDERSTAND": {"allowed_attributes": ["Dimension", "Widerstandattribut"]},
            },
        },
    )

    rules = load_attribute_rules(rules_path)

    assert rules.is_known("WIDERSTAND")
    assert rules.allowed_for("WIDERSTAND") == frozenset(
        {"Dimension", "Widerstandattribut"}
    )


def test_invalid_json_raises(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(InvalidRulesError):
        load_attribute_rules(rules_path)


def test_missing_sachgruppen_field_raises(tmp_path: Path) -> None:
    rules_path = _write_rules(tmp_path / "rules.json", {"version": 1})

    with pytest.raises(InvalidRulesError):
        load_attribute_rules(rules_path)


def test_invalid_allowed_attributes_type_raises(tmp_path: Path) -> None:
    rules_path = _write_rules(
        tmp_path / "rules.json",
        {"sachgruppen": {"WIDERSTAND": {"allowed_attributes": "Dimension"}}},
    )

    with pytest.raises(InvalidRulesError):
        load_attribute_rules(rules_path)
