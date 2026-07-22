"""Tests für den Online-Modus der Kommandozeilenanwendung."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from avor_smart_attribute_manager import cli
from avor_smart_attribute_manager.analysis import attribute_analyzer
from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)


class _FakeProvider(ComponentDataProvider):
    def __init__(self, provider_name: str = "mouser") -> None:
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    def search_exact(
        self, manufacturer_part_number: str, manufacturer: str | None = None
    ) -> ProviderSearchResult:
        return ProviderSearchResult(
            provider=self._name,
            status=ProviderResponseStatus.OK,
            products=(
                ProviderProduct(
                    manufacturer_part_number="LM317T",
                    manufacturer="Texas Instruments",
                    product_url="https://example.com/p",
                    parameters={"Tolerance": "1%"},
                ),
            ),
        )


def _write_erp(path: Path) -> Path:
    pd.DataFrame(
        {
            "ARTIKEL": ["A-1"],
            "SACHGRUPPENKLASSE": ["Widerstand"],
            "SachGruppe": ["Widerstand"],
            "Hersteller": ["Texas Instruments"],
            "HerstellerNr": ["LM317T"],
            "Toleranz": [None],
        }
    ).to_excel(path, index=False)
    return path


def _write_rules(path: Path) -> Path:
    import json

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


def test_online_missing_key_returns_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    erp = _write_erp(tmp_path / "ERP.xlsx")
    rules = _write_rules(tmp_path / "rules.json")

    exit_code = cli.main(
        ["analyse", str(erp), "--rules", str(rules), "--online", "--no-cache"]
    )

    assert exit_code == 2


def test_online_creates_sheets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        attribute_analyzer, "build_default_provider", lambda _settings: _FakeProvider()
    )
    monkeypatch.chdir(tmp_path)
    erp = _write_erp(tmp_path / "ERP.xlsx")
    rules = _write_rules(tmp_path / "rules.json")

    exit_code = cli.main(
        ["analyse", str(erp), "--rules", str(rules), "--online", "--no-cache"]
    )

    assert exit_code == 0
    output = tmp_path / "ERP_analyse.xlsx"
    assert output.is_file()
    sheets = pd.read_excel(output, sheet_name=None)
    assert "Online_Vorschlaege" in sheets
    assert "Online_Abgleich" in sheets
    assert sheets["Online_Vorschlaege"].iloc[0]["Attribut"] == "Toleranz"


def test_resolve_provider_names_default_is_none() -> None:
    assert cli._resolve_provider_names(None) is None
    assert cli._resolve_provider_names([]) is None


def test_resolve_provider_names_all_keyword() -> None:
    from avor_smart_attribute_manager.config.settings import SUPPORTED_PROVIDERS

    assert cli._resolve_provider_names(["all"]) == list(SUPPORTED_PROVIDERS)


def test_resolve_provider_names_dedupes_and_keeps_order() -> None:
    assert cli._resolve_provider_names(["nexar", "mouser", "nexar"]) == [
        "nexar",
        "mouser",
    ]


def test_online_multiple_providers_create_comparison_sheet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _build_providers(_settings: object, names: list[str]) -> list[_FakeProvider]:
        return [_FakeProvider(name) for name in names]

    monkeypatch.setattr(cli, "build_providers", _build_providers)
    monkeypatch.chdir(tmp_path)
    erp = _write_erp(tmp_path / "ERP.xlsx")
    rules = _write_rules(tmp_path / "rules.json")

    exit_code = cli.main(
        [
            "analyse",
            str(erp),
            "--rules",
            str(rules),
            "--online",
            "--no-cache",
            "--provider",
            "mouser",
            "--provider",
            "digikey",
        ]
    )

    assert exit_code == 0
    sheets = pd.read_excel(tmp_path / "ERP_analyse.xlsx", sheet_name=None)
    assert "Provider_Vergleich" in sheets
    assert not sheets["Provider_Vergleich"].empty
