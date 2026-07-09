"""Tests für die Spaltennormalisierung."""

from __future__ import annotations

import pytest

from avor_smart_attribute_manager.excel.columns import (
    normalize_column_name,
    normalize_columns,
)


@pytest.mark.parametrize(
    ("original", "expected"),
    [
        ("Dimmension", "Dimension"),
        ("SMD-Bauform", "SmdBauform"),
        ("Feeder-Typ", "Feeder"),
        ("Spannung-Primär", "Spannungprimaer"),
        ("Strom-Primär", "Stromprimaer"),
        ("Spannung-Sekundär", "Spannungsekundaer"),
        ("Strom-Sekundär", "Stromsekundaer"),
        ("Länge", "Laengeattribut"),
        ("Nutzengrösse", "Nutzengroesse"),
        ("Widerstand", "Widerstandattribut"),
    ],
)
def test_normalize_known_columns(original: str, expected: str) -> None:
    assert normalize_column_name(original) == expected


def test_normalize_trims_and_maps_with_whitespace() -> None:
    assert normalize_column_name("  Dimmension  ") == "Dimension"


def test_normalize_unknown_column_is_unchanged_but_trimmed() -> None:
    assert normalize_column_name("  ARTIKELNUMMER ") == "ARTIKELNUMMER"


def test_normalize_columns_preserves_order() -> None:
    columns = ["ARTIKELNUMMER", "Dimmension", "Feeder-Typ"]
    assert normalize_columns(columns) == ["ARTIKELNUMMER", "Dimension", "Feeder"]


def test_normalize_columns_maps_artikel_alias() -> None:
    columns = ["ARTIKEL", "SACHGRUPPENKLASSE", "Dimmension"]
    assert normalize_columns(columns) == [
        "ARTIKELNUMMER",
        "SACHGRUPPENKLASSE",
        "Dimension",
    ]


def test_normalize_columns_keeps_canonical_when_both_present() -> None:
    # Ist der kanonische Name bereits vorhanden, wird der Alias nicht umbenannt.
    columns = ["ARTIKELNUMMER", "ARTIKEL"]
    assert normalize_columns(columns) == ["ARTIKELNUMMER", "ARTIKEL"]
