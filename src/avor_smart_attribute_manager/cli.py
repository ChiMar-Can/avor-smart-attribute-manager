"""Kommandozeilen-Anwendung für die ERP-Datenqualitätsanalyse.

Ermöglicht eine erste lauffähige Nutzung ohne GUI:

* ``analyse <Datei>`` analysiert eine angegebene ERP-Excel-Datei.
* Ohne Argumente wird ein Dateiauswahldialog geöffnet (sofern verfügbar).

Die Eingabedatei wird ausschliesslich gelesen; das Ergebnis wird als neue Datei
``<Dateiname>_analyse.xlsx`` geschrieben.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from avor_smart_attribute_manager.analysis.attribute_analyzer import (
    AnalysisExport,
    analyze_and_export,
)
from avor_smart_attribute_manager.excel.exporter import build_summary_frame


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


def _print_summary(export: AnalysisExport) -> None:
    """Gibt den Ausgabepfad und die Kennzahlen auf der Konsole aus."""
    print(f"Analyse geschrieben: {export.output_path}")
    summary = build_summary_frame(export.results)
    for _, row in summary.iterrows():
        print(f"  {row['Kennzahl']}: {row['Wert']}")


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
    if args.command == "analyse":
        input_path = args.file
        rules_path = args.rules
        output_path = args.output
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

    try:
        export = analyze_and_export(
            input_path, output_path=output_path, rules_path=rules_path
        )
    except (OSError, ValueError) as error:
        print(f"Analyse fehlgeschlagen: {error}", file=sys.stderr)
        return 1

    _print_summary(export)
    return 0
