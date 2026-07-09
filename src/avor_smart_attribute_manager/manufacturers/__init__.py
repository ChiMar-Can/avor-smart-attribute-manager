"""Herstellerdaten.

Beheimatet die herstellerspezifische Auswertung von Artikeldaten (z. B.
Zuordnung anhand der Herstellernummer, Vereinheitlichung von Hersteller- und
Attributbezeichnungen).

Verantwortung:

* Aufbereitung und Abgleich von Herstellerinformationen.
* Nutzung der generischen Datenquellen-Abstraktion
  (:mod:`avor_smart_attribute_manager.datasources`) für spätere externe
  Quellen.

Wichtige Einschränkung im aktuellen Projektstand: Es werden **keine**
Hersteller-APIs angebunden und keine Firmendaten hinterlegt. Dieses Paket
beschreibt vorerst nur die Verantwortung und Struktur.
"""

from __future__ import annotations

__all__: list[str] = []
