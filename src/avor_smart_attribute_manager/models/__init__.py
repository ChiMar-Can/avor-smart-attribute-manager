"""Domänenmodelle (gemeinsame Datenstrukturen).

Enthält die zentralen, technologie-neutralen Datenstrukturen der Anwendung
(z. B. Artikel, Attribut, Analyseergebnis, Vorschlag). Diese Modelle werden
von mehreren Modulen gemeinsam genutzt und bilden das gemeinsame Vokabular
zwischen GUI, Analyse, Regelprüfung und Datenquellen.

Vorteil einer eigenen Modellschicht:

* Entkoppelt die fachlichen Begriffe von konkreten Bibliotheken (z. B. pandas
  oder PySide6).
* Erlaubt typsichere Schnittstellen zwischen den Modulen.

Aktuell definiert: :class:`~avor_smart_attribute_manager.models.article.Article`
sowie die Prüfergebnisse in
:mod:`avor_smart_attribute_manager.models.validation`.
"""

from __future__ import annotations

from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import (
    ArticleOnlineStatus,
    AttributeSuggestion,
    MatchConfidence,
    MatchStatus,
    OnlineAnalysis,
    ProductInfo,
    SuggestionAction,
)
from avor_smart_attribute_manager.models.validation import (
    ArticleValidationResult,
    CheckStatus,
)

__all__ = [
    "Article",
    "ArticleOnlineStatus",
    "ArticleValidationResult",
    "AttributeSuggestion",
    "CheckStatus",
    "MatchConfidence",
    "MatchStatus",
    "OnlineAnalysis",
    "ProductInfo",
    "SuggestionAction",
]
