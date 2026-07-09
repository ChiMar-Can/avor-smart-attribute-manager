"""Attributanalyse.

Beheimatet die Auswertung der Artikelattribute im Hinblick auf die
Datenqualität (z. B. fehlende, unvollständige oder uneinheitliche Attribute).

Verantwortung:

* Analyse der eingelesenen Daten und Erzeugung nachvollziehbarer Befunde.
* Ableitung von Verbesserungs-**vorschlägen** (nie automatische Änderungen).

Jeder Befund und jeder Vorschlag muss begründbar sein (Grundprinzip des
Projekts). Die Analyse ist unabhängig von der GUI und daher isoliert testbar.
"""

from __future__ import annotations

from avor_smart_attribute_manager.analysis.attribute_analyzer import (
    AnalysisExport,
    analyze_and_export,
    analyze_articles,
    analyze_workbook,
)

__all__ = [
    "AnalysisExport",
    "analyze_and_export",
    "analyze_articles",
    "analyze_workbook",
]
