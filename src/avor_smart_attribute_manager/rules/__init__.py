"""Regelprüfung.

Enthält die Prüfung der Daten gegen definierbare Regeln (z. B. Pflichtfelder,
Formatvorgaben, erlaubte Wertebereiche, Namenskonventionen).

Verantwortung:

* Verwaltung eines Satzes von Regeln.
* Anwendung der Regeln auf die Daten und Erzeugung nachvollziehbarer
  Regelverstösse als Vorschläge zur Korrektur.

Die Regeln sollen später konfigurierbar/erweiterbar sein, ohne den Kerncode zu
ändern (offene Erweiterbarkeit). Es werden hier keine konkreten Regeln
erfunden.
"""

from __future__ import annotations

__all__: list[str] = []
