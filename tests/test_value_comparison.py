"""Tests für den Wertevergleich mit Einheiten-Normalisierung."""

from __future__ import annotations

from avor_smart_attribute_manager.analysis.value_comparison import (
    normalize_value,
    values_match,
)


def test_normalize_removes_spaces_and_case() -> None:
    assert normalize_value(" 10 K ") == "10k"


def test_decimal_comma_equals_dot() -> None:
    assert values_match("1,5A", "1.5 A")


def test_symbol_variants_match() -> None:
    assert values_match("10\u00b5F", "10uF")
    assert values_match("4.7\u2126", "4.7 ohm")


def test_clear_mismatch() -> None:
    assert not values_match("10k", "100k")
