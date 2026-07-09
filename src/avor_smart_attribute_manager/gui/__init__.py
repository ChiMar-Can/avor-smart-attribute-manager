"""Grafische Benutzeroberfläche (GUI).

Enthält die gesamte Präsentationsschicht auf Basis von PySide6 (Qt).

Verantwortung:

* Darstellung der Daten und Analyseergebnisse.
* Entgegennahme von Benutzeraktionen (Datei öffnen, Analyse starten,
  Vorschläge ansehen/exportieren).

Wichtige Regel für dieses Paket:

* Die GUI enthält **keine** Geschäftslogik. Sie ruft ausschliesslich die
  Fachmodule (Analyse, Regelprüfung, Excel-Import/-Export) auf und stellt
  deren Ergebnisse dar. Dadurch bleiben GUI und Businesslogik sauber
  getrennt und die Logik ist unabhängig von Qt testbar.
"""

from __future__ import annotations

__all__: list[str] = []
