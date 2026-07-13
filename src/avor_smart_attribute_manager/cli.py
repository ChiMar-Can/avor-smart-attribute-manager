"""Kommandozeilen-Anwendung für die ERP-Datenqualitätsanalyse.

Ermöglicht eine erste lauffähige Nutzung ohne GUI:

* ``analyse <Datei>`` analysiert eine angegebene ERP-Excel-Datei.
* Ohne Argumente wird ein Dateiauswahldialog geöffnet (sofern verfügbar).

Die Eingabedatei wird ausschliesslich gelesen; das Ergebnis wird als neue Datei
``<Dateiname>_analyse.xlsx`` geschrieben.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from avor_smart_attribute_manager.analysis.attribute_analyzer import (
    AnalysisExport,
    OnlineAnalysisExport,
    analyze_and_export,
    analyze_and_export_with_online,
)
from avor_smart_attribute_manager.config.settings import (
    SUPPORTED_PROVIDERS,
    load_settings,
)
from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.digikey import DigiKeyApiVersion
from avor_smart_attribute_manager.datasources.provider import MissingApiKeyError
from avor_smart_attribute_manager.excel.exporter import build_summary_frame
from avor_smart_attribute_manager.models.online import MatchStatus


def _build_parser() -> argparse.ArgumentParser:
    """Erstellt den Argumentparser der Anwendung."""
    parser = argparse.ArgumentParser(
        prog="avor-smart-attribute-manager",
        description="Analysiert die Datenqualität von ERP-Artikelstammdaten.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyse = subparsers.add_parser(
        "analyse", help="Eine ERP-Excel-Datei analysieren."
    )
    analyse.add_argument("file", type=Path, help="Pfad zur ERP-Excel-Datei.")
    analyse.add_argument(
        "--rules",
        type=Path,
        default=None,
        help="Optionaler Pfad zu einer Regelwerksdatei (Standard: mitgeliefert).",
    )
    analyse.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optionaler Zielpfad (Standard: <Dateiname>_analyse.xlsx).",
    )
    analyse.add_argument(
        "--online",
        action="store_true",
        help=(
            "Zusätzlich einen Online-Abgleich der HerstellerNr durchführen "
            "(benötigt Zugangsdaten des gewählten Providers)."
        ),
    )
    analyse.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help=(
            "Datenquelle für den Online-Abgleich (Standard: Konfiguration bzw. "
            "mouser)."
        ),
    )
    analyse.add_argument(
        "--digikey-version",
        choices=[version.value for version in DigiKeyApiVersion],
        default=None,
        help=(
            "DigiKey-API-Version für den Online-Abgleich (Standard: Konfiguration "
            "bzw. v4)."
        ),
    )
    analyse.add_argument(
        "--no-cache",
        action="store_true",
        help="Lokalen Cache für den Online-Abgleich deaktivieren.",
    )
    analyse.add_argument(
        "--clear-cache",
        action="store_true",
        help="Lokalen Cache vor dem Lauf vollständig löschen.",
    )
    return parser


def _select_input_file() -> Path | None:
    """Öffnet einen Dateiauswahldialog und liefert den gewählten Pfad.

    Returns:
        Der ausgewählte Pfad oder ``None``, wenn kein Dialog verfügbar ist oder
        die Auswahl abgebrochen wurde.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    try:
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(
            title="ERP-Excel-Datei auswählen",
            filetypes=[("Excel-Dateien", "*.xlsx *.xls"), ("Alle Dateien", "*.*")],
        )
        root.destroy()
    except tk.TclError:
        return None

    return Path(selected) if selected else None


def _print_summary(output_path: Path, export: AnalysisExport | OnlineAnalysisExport) -> None:
    """Gibt den Ausgabepfad und die Kennzahlen auf der Konsole aus."""
    print(f"Analyse geschrieben: {output_path}")
    summary = build_summary_frame(export.results)
    for _, row in summary.iterrows():
        print(f"  {row['Kennzahl']}: {row['Wert']}")


def _print_online_summary(export: OnlineAnalysisExport) -> None:
    """Gibt Kennzahlen des Online-Abgleichs auf der Konsole aus."""
    statuses = export.online.statuses
    exact = sum(1 for s in statuses if s.match_status is MatchStatus.EXACT_MATCH)
    print("  Online-Abgleich:")
    print(f"    Artikel abgeglichen: {len(statuses)}")
    print(f"    Exakte Treffer: {exact}")
    print(f"    Vorschläge: {len(export.online.suggestions)}")


def main(argv: list[str] | None = None) -> int:
    """Einstiegspunkt der Kommandozeilenanwendung.

    Args:
        argv: Optionale Argumentliste (vor allem für Tests). Ohne Angabe werden
            die Prozessargumente verwendet.

    Returns:
        Prozess-Exit-Code (``0`` bei Erfolg).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    rules_path: Path | None = None
    output_path: Path | None = None
    online = False
    no_cache = False
    clear_cache = False
    provider_override: str | None = None
    digikey_version_override: str | None = None
    if args.command == "analyse":
        input_path = args.file
        rules_path = args.rules
        output_path = args.output
        online = args.online
        no_cache = args.no_cache
        clear_cache = args.clear_cache
        provider_override = args.provider
        digikey_version_override = args.digikey_version
    else:
        selected = _select_input_file()
        if selected is None:
            parser.print_help(sys.stderr)
            print("\nKeine Datei ausgewählt.", file=sys.stderr)
            return 2
        input_path = selected

    if not input_path.is_file():
        print(f"Datei nicht gefunden: {input_path}", file=sys.stderr)
        return 2

    if online:
        settings = load_settings()
        if provider_override is not None:
            settings = dataclasses.replace(settings, provider=provider_override)
        if digikey_version_override is not None:
            settings = dataclasses.replace(
                settings,
                digikey_api_version=DigiKeyApiVersion.from_str(
                    digikey_version_override
                ),
            )
        if no_cache:
            settings = dataclasses.replace(settings, use_cache=False)
        if clear_cache:
            SearchCache(settings.cache_dir, settings.cache_ttl_seconds).clear()
        try:
            online_export = analyze_and_export_with_online(
                input_path,
                output_path=output_path,
                rules_path=rules_path,
                settings=settings,
            )
        except MissingApiKeyError as error:
            print(f"Online-Abgleich nicht möglich: {error}", file=sys.stderr)
            return 2
        except (OSError, ValueError) as error:
            print(f"Analyse fehlgeschlagen: {error}", file=sys.stderr)
            return 1
        _print_summary(online_export.output_path, online_export)
        _print_online_summary(online_export)
        return 0

    try:
        export = analyze_and_export(
            input_path, output_path=output_path, rules_path=rules_path
        )
    except (OSError, ValueError) as error:
        print(f"Analyse fehlgeschlagen: {error}", file=sys.stderr)
        return 1

    _print_summary(export.output_path, export)
    return 0
