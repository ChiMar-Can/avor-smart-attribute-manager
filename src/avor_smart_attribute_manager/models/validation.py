"""Domänenmodell für Ergebnisse der Regelprüfung.

Definiert das interne Ergebnisobjekt je Artikel. Es enthält bewusst noch keine
Excel-/Ausgabelogik – lediglich das strukturierte Prüfergebnis, das später von
GUI und Export weiterverwendet werden kann.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """Gesamtstatus der Prüfung eines Artikels.

    Attributes:
        OK: Sachgruppe bekannt; keine fehlenden und keine unzulässig gefüllten
            Attribute.
        UNKNOWN_SACHGRUPPE: Die Sachgruppenklasse ist im Regelwerk nicht
            hinterlegt; es kann keine Attributprüfung erfolgen.
        ISSUES_FOUND: Sachgruppe bekannt, aber es fehlen relevante Attribute
            und/oder es sind nicht vorgesehene Attribute gefüllt.
    """

    OK = "ok"
    UNKNOWN_SACHGRUPPE = "unknown_sachgruppe"
    ISSUES_FOUND = "issues_found"


@dataclass(frozen=True)
class ArticleValidationResult:
    """Prüfergebnis für einen einzelnen Artikel.

    Attributes:
        article_number: Artikelnummer des geprüften Artikels.
        sachgruppenklasse: Sachgruppenklasse des Artikels.
        allowed_attributes: Für die Sachgruppe laut Regelwerk erlaubte/relevante
            Attribute (leer, wenn die Sachgruppe unbekannt ist).
        missing_attributes: Erlaubte Attribute, die im Artikel fehlen oder leer
            sind.
        disallowed_filled_attributes: Attribute, die gefüllt sind, obwohl sie
            für die Sachgruppe nicht vorgesehen sind.
        status: Zusammenfassender Prüfstatus (siehe :class:`CheckStatus`).
    """

    article_number: str
    sachgruppenklasse: str
    allowed_attributes: tuple[str, ...]
    missing_attributes: tuple[str, ...]
    disallowed_filled_attributes: tuple[str, ...]
    status: CheckStatus
