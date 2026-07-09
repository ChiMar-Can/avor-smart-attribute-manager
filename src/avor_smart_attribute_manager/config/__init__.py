"""Konfiguration der Anwendung.

Bündelt sämtliche einstellbaren Parameter des Werkzeugs an einer zentralen
Stelle, damit sie nicht über den Code verstreut sind.

Verantwortung:

* Laden und Bereitstellen von Anwendungseinstellungen (z. B. Pfade, Sprache,
  Grenzwerte für Analysen).
* Trennung von Standardwerten und benutzer-/umgebungsspezifischen Werten.

Wichtig: Hier werden **keine** Zugangsdaten oder Firmendaten fest hinterlegt.
Geheimnisse (z. B. spätere API-Schlüssel) gehören in Umgebungsvariablen bzw.
lokale, nicht versionierte Dateien.
"""

from __future__ import annotations

__all__: list[str] = []
