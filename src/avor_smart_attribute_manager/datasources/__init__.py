"""Datenquellen (Abstraktion externer Datenlieferanten).

Definiert eine einheitliche, technologie-neutrale Schnittstelle für externe
Datenquellen (z. B. später Hersteller-Portale, Distributoren-Kataloge oder
lokale Referenzdaten).

Zweck der Abstraktion:

* Die Fachmodule (Analyse, Regelprüfung, Herstellerdaten) hängen nur von der
  Schnittstelle ab, nicht von einer konkreten Quelle.
* Neue Quellen lassen sich ergänzen, ohne bestehenden Code zu ändern.

Wichtige Einschränkung im aktuellen Projektstand: Es werden **noch keine**
externen APIs angebunden. Dieses Paket definiert vorerst nur die Schnittstelle.
"""

from __future__ import annotations

from avor_smart_attribute_manager.datasources.base import DataSource

__all__ = ["DataSource"]
