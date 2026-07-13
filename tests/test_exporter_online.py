"""Tests für den Excel-Export der Online-Blätter."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from avor_smart_attribute_manager.excel.exporter import (
    ANALYSIS_SHEET_NAME,
    ONLINE_STATUS_COLUMNS,
    ONLINE_STATUS_SHEET_NAME,
    ONLINE_SUGGESTIONS_COLUMNS,
    ONLINE_SUGGESTIONS_SHEET_NAME,
    SUMMARY_SHEET_NAME,
    build_online_status_frame,
    build_online_suggestions_frame,
    export_analysis_with_online,
)
from avor_smart_attribute_manager.models.online import (
    ArticleOnlineStatus,
    AttributeSuggestion,
    MatchConfidence,
    MatchStatus,
    SuggestionAction,
)
from avor_smart_attribute_manager.models.validation import (
    ArticleValidationResult,
    CheckStatus,
)


def _suggestion() -> AttributeSuggestion:
    return AttributeSuggestion(
        article_number="A-1",
        sachgruppe="Widerstand",
        attribute="Toleranz",
        erp_value=None,
        suggested_value="1%",
        action=SuggestionAction.ERGAENZEN,
        provider="mouser",
        source_mpn="LM317T",
        source_manufacturer="Texas Instruments",
        match_status=MatchStatus.EXACT_MATCH,
        confidence=MatchConfidence.HOCH,
        product_url="https://example.com/p",
        datasheet_url="https://example.com/ds",
        reason="ERP-Wert leer, Online-Wert vorhanden.",
    )


def _status() -> ArticleOnlineStatus:
    return ArticleOnlineStatus(
        article_number="A-1",
        sachgruppe="Widerstand",
        manufacturer="Texas Instruments",
        manufacturer_part_number="LM317T",
        provider="mouser",
        match_status=MatchStatus.EXACT_MATCH,
        match_count=1,
        message=None,
    )


def test_suggestions_frame_columns_and_labels() -> None:
    frame = build_online_suggestions_frame([_suggestion()])
    assert list(frame.columns) == list(ONLINE_SUGGESTIONS_COLUMNS)
    assert frame.iloc[0]["Aktion"] == "Ergänzen"
    assert frame.iloc[0]["Match_Status"] == "Exakter Treffer"
    assert frame.iloc[0]["Match_Konfidenz"] == "Hoch"


def test_empty_suggestions_frame_has_header() -> None:
    frame = build_online_suggestions_frame([])
    assert list(frame.columns) == list(ONLINE_SUGGESTIONS_COLUMNS)
    assert frame.empty


def test_status_frame_columns() -> None:
    frame = build_online_status_frame([_status()])
    assert list(frame.columns) == list(ONLINE_STATUS_COLUMNS)
    assert frame.iloc[0]["Match_Status"] == "Exakter Treffer"


def test_export_writes_all_sheets(tmp_path: Path) -> None:
    original = pd.DataFrame(
        {"ARTIKELNUMMER": ["A-1"], "SACHGRUPPENKLASSE": ["Widerstand"]}
    )
    results = [
        ArticleValidationResult(
            article_number="A-1",
            sachgruppenklasse="Widerstand",
            allowed_attributes=("Toleranz",),
            filled_attributes=(),
            missing_attributes=("Toleranz",),
            disallowed_filled_attributes=(),
            status=CheckStatus.ISSUES_FOUND,
        )
    ]
    target = tmp_path / "erp_analyse.xlsx"

    out = export_analysis_with_online(
        original,
        results,
        [_suggestion()],
        [_status()],
        tmp_path / "erp.xlsx",
        target,
    )

    assert out == target
    sheets = pd.read_excel(target, sheet_name=None)
    assert set(sheets) == {
        ANALYSIS_SHEET_NAME,
        SUMMARY_SHEET_NAME,
        ONLINE_SUGGESTIONS_SHEET_NAME,
        ONLINE_STATUS_SHEET_NAME,
    }
    assert sheets[ONLINE_SUGGESTIONS_SHEET_NAME].iloc[0]["Attribut"] == "Toleranz"
