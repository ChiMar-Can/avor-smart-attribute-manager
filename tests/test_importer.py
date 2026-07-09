"""Tests für den Excel-Import."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from avor_smart_attribute_manager.excel.importer import (
    MissingBaseColumnsError,
    load_articles,
    to_articles,
)


def _write_excel(path: Path, frame: pd.DataFrame) -> Path:
    """Schreibt einen ``DataFrame`` als Excel-Datei und liefert den Pfad."""
    frame.to_excel(path, index=False)
    return path


def test_load_articles_reads_and_normalizes_columns(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "ARTIKELNUMMER": ["A-1"],
            "SACHGRUPPENKLASSE": ["WIDERSTAND"],
            "Dimmension": ["0805"],
            "Feeder-Typ": ["8mm"],
        }
    )
    excel_path = _write_excel(tmp_path / "erp.xlsx", frame)

    articles = load_articles(excel_path)

    assert len(articles) == 1
    article = articles[0]
    assert article.article_number == "A-1"
    assert article.sachgruppenklasse == "WIDERSTAND"
    assert set(article.attributes) == {"Dimension", "Feeder"}
    assert article.attributes["Dimension"] == "0805"


def test_empty_values_are_normalized_to_none() -> None:
    frame = pd.DataFrame(
        {
            "ARTIKELNUMMER": ["A-1"],
            "SACHGRUPPENKLASSE": ["WIDERSTAND"],
            "Dimension": [None],
            "Feeder": ["   "],
        }
    )

    article = to_articles(frame)[0]

    assert article.attributes["Dimension"] is None
    assert article.attributes["Feeder"] is None


def test_missing_base_columns_raise(tmp_path: Path) -> None:
    frame = pd.DataFrame({"ARTIKELNUMMER": ["A-1"], "Dimension": ["0805"]})
    excel_path = _write_excel(tmp_path / "erp.xlsx", frame)

    with pytest.raises(MissingBaseColumnsError):
        load_articles(excel_path)


def test_original_file_is_not_modified(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {"ARTIKELNUMMER": ["A-1"], "SACHGRUPPENKLASSE": ["WIDERSTAND"]}
    )
    excel_path = _write_excel(tmp_path / "erp.xlsx", frame)
    before = excel_path.read_bytes()

    load_articles(excel_path)

    assert excel_path.read_bytes() == before
