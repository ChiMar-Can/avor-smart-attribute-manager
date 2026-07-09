"""Tests für den Excel-Export der Analyseergebnisse."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from avor_smart_attribute_manager.excel.exporter import (
    ANALYSIS_COLUMNS,
    ANALYSIS_SHEET_NAME,
    SUMMARY_SHEET_NAME,
    RowCountMismatchError,
    analysis_output_path,
    build_analysis_frame,
    build_summary_frame,
    export_analysis,
)
from avor_smart_attribute_manager.models.validation import (
    ArticleValidationResult,
    CheckStatus,
)


def _result(
    *,
    number: str = "A-1",
    sachgruppe: str = "Widerstand",
    allowed: tuple[str, ...] = (),
    filled: tuple[str, ...] = (),
    missing: tuple[str, ...] = (),
    disallowed: tuple[str, ...] = (),
    status: CheckStatus = CheckStatus.OK,
) -> ArticleValidationResult:
    return ArticleValidationResult(
        article_number=number,
        sachgruppenklasse=sachgruppe,
        allowed_attributes=allowed,
        filled_attributes=filled,
        missing_attributes=missing,
        disallowed_filled_attributes=disallowed,
        status=status,
    )


def test_analysis_output_path_appends_suffix() -> None:
    assert analysis_output_path(Path("/data/ERP_Export.xlsx")) == Path(
        "/data/ERP_Export_analyse.xlsx"
    )


def test_build_analysis_frame_keeps_original_and_appends_columns() -> None:
    original = pd.DataFrame(
        {
            "ARTIKELNUMMER": ["A-1"],
            "SACHGRUPPENKLASSE": ["Widerstand"],
            "SMD-Bauform": ["0805"],
        }
    )
    results = [
        _result(
            allowed=("Wert", "Toleranz"),
            filled=("SmdBauform",),
            missing=("Wert", "Toleranz"),
            disallowed=("SmdBauform",),
            status=CheckStatus.ISSUES_FOUND,
        )
    ]

    frame = build_analysis_frame(original, results)

    # Originalspalten bleiben erhalten und stehen vorne.
    assert list(frame.columns) == [
        "ARTIKELNUMMER",
        "SACHGRUPPENKLASSE",
        "SMD-Bauform",
        *ANALYSIS_COLUMNS,
    ]
    row = frame.iloc[0]
    assert row["SMD-Bauform"] == "0805"
    assert row["Pruefstatus"] == "Fehler gefunden"
    assert row["Erlaubte_Attribute"] == "Wert, Toleranz"
    assert row["Gefuellte_Attribute"] == "SmdBauform"
    assert row["Fehlende_Attribute"] == "Wert, Toleranz"
    assert row["Nicht_erlaubte_gefuellte_Attribute"] == "SmdBauform"
    assert row["Anzahl_fehlender_Attribute"] == 2
    assert row["Anzahl_unzulaessiger_Attribute"] == 1


def test_build_analysis_frame_does_not_mutate_original() -> None:
    original = pd.DataFrame({"ARTIKELNUMMER": ["A-1"], "SACHGRUPPENKLASSE": ["X"]})

    build_analysis_frame(original, [_result(status=CheckStatus.UNKNOWN_SACHGRUPPE)])

    assert list(original.columns) == ["ARTIKELNUMMER", "SACHGRUPPENKLASSE"]


def test_build_analysis_frame_row_mismatch_raises() -> None:
    original = pd.DataFrame({"ARTIKELNUMMER": ["A-1", "A-2"]})

    with pytest.raises(RowCountMismatchError):
        build_analysis_frame(original, [_result()])


def test_build_summary_frame_counts() -> None:
    results = [
        _result(status=CheckStatus.OK),
        _result(status=CheckStatus.ISSUES_FOUND, missing=("Wert",)),
        _result(status=CheckStatus.ISSUES_FOUND, disallowed=("Feeder",)),
        _result(status=CheckStatus.UNKNOWN_SACHGRUPPE),
    ]

    frame = build_summary_frame(results)
    summary = dict(zip(frame["Kennzahl"], frame["Wert"], strict=True))

    assert summary["Anzahl Artikel"] == 4
    assert summary["Anzahl OK"] == 1
    assert summary["Anzahl unbekannte Sachgruppen"] == 1
    assert summary["Anzahl Artikel mit fehlenden Attributen"] == 1
    assert summary["Anzahl Artikel mit unzulässigen Attributen"] == 1


def test_export_analysis_writes_two_sheets(tmp_path: Path) -> None:
    original = pd.DataFrame(
        {"ARTIKELNUMMER": ["A-1"], "SACHGRUPPENKLASSE": ["Widerstand"]}
    )
    input_path = tmp_path / "ERP_Export.xlsx"
    # Datei muss nicht existieren; nur der Name wird abgeleitet.
    output = export_analysis(original, [_result()], input_path)

    assert output == tmp_path / "ERP_Export_analyse.xlsx"
    assert output.is_file()
    sheets = pd.ExcelFile(output).sheet_names
    assert sheets == [ANALYSIS_SHEET_NAME, SUMMARY_SHEET_NAME]
