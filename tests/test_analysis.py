"""End-to-End-Tests der Attributanalyse (Import + Regelprüfung)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from avor_smart_attribute_manager.analysis.attribute_analyzer import analyze_workbook
from avor_smart_attribute_manager.models.validation import CheckStatus


def test_analyze_workbook_end_to_end(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "ARTIKELNUMMER": ["A-1", "A-2", "A-3"],
            "SACHGRUPPENKLASSE": ["WIDERSTAND", "WIDERSTAND", "UNBEKANNT"],
            "Dimmension": ["0805", "0603", "0402"],
            "Widerstand": ["10k", None, "1k"],
            "Feeder-Typ": [None, "8mm", None],
        }
    )
    excel_path = tmp_path / "erp.xlsx"
    frame.to_excel(excel_path, index=False)

    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps(
            {
                "sachgruppen": {
                    "WIDERSTAND": {
                        "allowed_attributes": ["Dimension", "Widerstandattribut"]
                    },
                    # Damit "Feeder" ein bekanntes Attribut ist (Universum),
                    # für WIDERSTAND aber unzulässig.
                    "SPULE": {"allowed_attributes": ["Feeder"]},
                }
            }
        ),
        encoding="utf-8",
    )

    results = analyze_workbook(excel_path, rules_path)

    assert [result.status for result in results] == [
        CheckStatus.OK,
        CheckStatus.ISSUES_FOUND,
        CheckStatus.UNKNOWN_SACHGRUPPE,
    ]
    # A-2: Widerstandattribut fehlt und Feeder ist unzulässig gefüllt.
    assert results[1].missing_attributes == ("Widerstandattribut",)
    assert results[1].disallowed_filled_attributes == ("Feeder",)
