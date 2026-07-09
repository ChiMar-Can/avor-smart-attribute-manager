"""Domänenmodell für Artikel und deren Attribute.

Enthält die technologie-neutrale Repräsentation eines Artikels (eine Zeile des
ERP-Exports). Das Modell ist bewusst frei von pandas/Qt, damit es von mehreren
Modulen (Analyse, Regelprüfung, GUI) gemeinsam genutzt werden kann.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Article:
    """Ein einzelner Artikel aus einem ERP-Export.

    Attributes:
        article_number: Eindeutige Artikelnummer.
        sachgruppenklasse: Sachgruppenklasse des Artikels; steuert, welche
            Attribute laut Regelwerk relevant sind.
        attributes: Zuordnung von (normalisiertem) Attributnamen zu Wert. Leere
            Werte werden bereits beim Import zu ``None`` vereinheitlicht, sodass
            nachgelagerte Prüfungen ohne pandas-Kenntnis auskommen.
    """

    article_number: str
    sachgruppenklasse: str
    attributes: Mapping[str, object]
