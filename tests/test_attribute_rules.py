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


def test_load_bundled_default_rules_is_populated() -> None:
    rules = load_attribute_rules()

    # Das mitgelieferte Regelwerk wird aus dem Attribut-Katalog generiert.
    assert "Widerstand" in rules.known_sachgruppen
    assert "Feeder" in rules.allowed_for("Widerstand")
    # Normalisierte Attributnamen werden verwendet (nicht die Rohnamen).
    assert "Widerstandattribut" in rules.allowed_for("Transistor")
    assert "SMD-Bauform" not in rules.allowed_for("Widerstand")


def test_allgemein_is_not_a_standalone_sachgruppe() -> None:
    rules = load_attribute_rules()

    assert "Allgemein" not in rules.known_sachgruppen
    assert not rules.is_known("Allgemein")


def test_global_attributes_are_prepended_and_deduplicated(tmp_path: Path) -> None:
    rules_path = _write_rules(
        tmp_path / "rules.json",
        {
            "sachgruppen": {
                "Allgemein": {"allowed_attributes": ["Technologie", "Typ", "Bemerkung"]},
                "Diode": {"allowed_attributes": ["Typ", "Wert", "Bemerkung"]},
            }
        },
    )

    rules = load_attribute_rules(rules_path)

    # Allgemein-Attribute zuerst, danach die spezifischen; Duplikate entfernt,
    # Reihenfolge beibehalten.
    assert rules.allowed_for("Diode") == ("Technologie", "Typ", "Bemerkung", "Wert")
    assert "Allgemein" not in rules.known_sachgruppen


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
    assert rules.allowed_for("WIDERSTAND") == ("Dimension", "Widerstandattribut")


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
