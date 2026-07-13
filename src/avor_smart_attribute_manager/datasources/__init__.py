"""Datenquellen (Abstraktion externer Datenlieferanten).

Definiert eine einheitliche, technologie-neutrale Schnittstelle für externe
Datenquellen (z. B. später Hersteller-Portale, Distributoren-Kataloge oder
lokale Referenzdaten).

Zweck der Abstraktion:

* Die Fachmodule (Analyse, Regelprüfung, Herstellerdaten) hängen nur von der
  Schnittstelle ab, nicht von einer konkreten Quelle.
* Neue Quellen lassen sich ergänzen, ohne bestehenden Code zu ändern.

Konkrete Provider (aktuell: Mouser) implementieren die Schnittstelle
:class:`ComponentDataProvider` und liefern ihre Ergebnisse ausschliesslich in
neutralen Datenmodellen. Weitere Provider (z. B. DigiKey, Nexar) lassen sich
ergänzen, ohne die Fachlogik zu ändern.
"""

from __future__ import annotations

from avor_smart_attribute_manager.datasources.base import DataSource
from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    MissingApiKeyError,
    ProviderError,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)

__all__ = [
    "ComponentDataProvider",
    "DataSource",
    "MissingApiKeyError",
    "ProviderError",
    "ProviderProduct",
    "ProviderResponseStatus",
    "ProviderSearchResult",
]
