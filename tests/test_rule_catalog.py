"""Tests für das Einlesen des Attribut-Katalogs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from avor_smart_attribute_manager.excel.rule_catalog import (
    CatalogFormatError,
    read_attribute_catalog,
)


def _write_catalog(path: Path, rows: list[tuple[str | None, str | None]]) -> Path:
    frame = pd.DataFrame(rows, columns=["Sachgruppe", "Attribut"])
    frame.to_excel(path, index=False)
    return path


def test_catalog_groups_and_normalizes_attributes(tmp_path: Path) -> None:
    catalog = _write_catalog(
        tmp_path / "catalog.xlsx",
        [
            ("Widerstand", "Technologie"),
            ("Widerstand", "SMD-Bauform"),
            ("Widerstand", "Feeder-Typ"),
            ("Leiterplatte", "Nutzengrösse"),
        ],
    )

    mapping = read_attribute_catalog(catalog)

    assert mapping["Widerstand"] == ["Technologie", "SmdBauform", "Feeder"]
    assert mapping["Leiterplatte"] == ["Nutzengroesse"]


def test_catalog_deduplicates_preserving_order(tmp_path: Path) -> None:
    catalog = _write_catalog(
        tmp_path / "catalog.xlsx",
        [
            ("Diode", "Typ"),
            ("Diode", "Wert"),
            ("Diode", "Typ"),
        ],
    )

    assert read_attribute_catalog(catalog)["Diode"] == ["Typ", "Wert"]


def test_catalog_skips_empty_rows(tmp_path: Path) -> None:
    catalog = _write_catalog(
        tmp_path / "catalog.xlsx",
        [
            ("Diode", "Typ"),
            (None, "Wert"),
            ("Diode", None),
        ],
    )

    assert read_attribute_catalog(catalog) == {"Diode": ["Typ"]}


def test_catalog_missing_columns_raise(tmp_path: Path) -> None:
    path = tmp_path / "catalog.xlsx"
    pd.DataFrame({"Sachgruppe": ["Diode"]}).to_excel(path, index=False)

    with pytest.raises(CatalogFormatError):
        read_attribute_catalog(path)
