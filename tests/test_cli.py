"""Tests für die Kommandozeilenanwendung."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from avor_smart_attribute_manager import cli


def _write_rules(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "description": "test",
                "sachgruppen": {
                    "Widerstand": {"allowed_attributes": ["Wert", "Toleranz"]}
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_erp(path: Path) -> Path:
    pd.DataFrame(
        {
            "ARTIKELNUMMER": ["A-1", "A-2"],
            "SACHGRUPPENKLASSE": ["Widerstand", "Unbekannt"],
            "Wert": ["10k", None],
        }
    ).to_excel(path, index=False)
    return path


def test_analyse_subcommand_creates_analysis_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    erp = _write_erp(tmp_path / "ERP_Export.xlsx")
    rules = _write_rules(tmp_path / "rules.json")

    exit_code = cli.main(["analyse", str(erp), "--rules", str(rules)])

    assert exit_code == 0
    output = tmp_path / "ERP_Export_analyse.xlsx"
    assert output.is_file()
    # Konsolenausgabe enthält den Pfad und Kennzahlen.
    captured = capsys.readouterr().out
    assert "ERP_Export_analyse.xlsx" in captured
    assert "Anzahl Artikel: 2" in captured


def test_analyse_respects_output_option(tmp_path: Path) -> None:
    erp = _write_erp(tmp_path / "ERP_Export.xlsx")
    rules = _write_rules(tmp_path / "rules.json")
    target = tmp_path / "custom.xlsx"

    exit_code = cli.main(
        ["analyse", str(erp), "--rules", str(rules), "--output", str(target)]
    )

    assert exit_code == 0
    assert target.is_file()


def test_original_file_is_not_modified(tmp_path: Path) -> None:
    erp = _write_erp(tmp_path / "ERP_Export.xlsx")
    rules = _write_rules(tmp_path / "rules.json")
    before = erp.read_bytes()

    cli.main(["analyse", str(erp), "--rules", str(rules)])

    assert erp.read_bytes() == before


def test_missing_file_returns_error(tmp_path: Path) -> None:
    exit_code = cli.main(["analyse", str(tmp_path / "does_not_exist.xlsx")])
    assert exit_code == 2


def test_no_command_uses_file_dialog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    erp = _write_erp(tmp_path / "ERP_Export.xlsx")
    monkeypatch.setattr(cli, "_select_input_file", lambda: erp)

    exit_code = cli.main([])

    assert exit_code == 0
    assert (tmp_path / "ERP_Export_analyse.xlsx").is_file()


def test_no_command_without_selection_returns_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "_select_input_file", lambda: None)
    assert cli.main([]) == 2
