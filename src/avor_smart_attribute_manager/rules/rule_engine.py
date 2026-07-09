"""Regelauswertung je Artikel.

Wendet das Sachgruppen-/Attribut-Regelwerk (siehe
:mod:`avor_smart_attribute_manager.rules.attribute_rules`) auf Artikel an und
erzeugt ein nachvollziehbares Prüfergebnis.

Grundregeln:

* Es werden **keine** Werte verändert – nur geprüft.
* Für jeden Artikel wird festgestellt, ob die Sachgruppe bekannt ist, welche
  erlaubten Attribute fehlen und welche nicht vorgesehenen Attribute gefüllt
  sind.
"""

from __future__ import annotations

from collections.abc import Iterable

from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.validation import (
    ArticleValidationResult,
    CheckStatus,
)
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules


def validate_article(article: Article, rules: AttributeRules) -> ArticleValidationResult:
    """Prüft einen einzelnen Artikel gegen das Regelwerk.

    Ein Attribut gilt als *gefüllt*, wenn sein Wert nicht ``None`` ist. Leere
    Werte werden bereits beim Import zu ``None`` vereinheitlicht.

    Args:
        article: Der zu prüfende Artikel.
        rules: Das anzuwendende Regelwerk.

    Returns:
        Das strukturierte Prüfergebnis des Artikels.
    """
    if not rules.is_known(article.sachgruppenklasse):
        return ArticleValidationResult(
            article_number=article.article_number,
            sachgruppenklasse=article.sachgruppenklasse,
            allowed_attributes=(),
            missing_attributes=(),
            disallowed_filled_attributes=(),
            status=CheckStatus.UNKNOWN_SACHGRUPPE,
        )

    allowed = rules.allowed_for(article.sachgruppenklasse)
    filled = {name for name, value in article.attributes.items() if value is not None}

    missing = allowed - filled
    disallowed_filled = filled - allowed

    status = (
        CheckStatus.OK
        if not missing and not disallowed_filled
        else CheckStatus.ISSUES_FOUND
    )

    return ArticleValidationResult(
        article_number=article.article_number,
        sachgruppenklasse=article.sachgruppenklasse,
        allowed_attributes=tuple(sorted(allowed)),
        missing_attributes=tuple(sorted(missing)),
        disallowed_filled_attributes=tuple(sorted(disallowed_filled)),
        status=status,
    )


def validate_articles(
    articles: Iterable[Article], rules: AttributeRules
) -> list[ArticleValidationResult]:
    """Prüft mehrere Artikel gegen das Regelwerk.

    Args:
        articles: Die zu prüfenden Artikel.
        rules: Das anzuwendende Regelwerk.

    Returns:
        Liste der Prüfergebnisse in der Reihenfolge der Eingabe.
    """
    return [validate_article(article, rules) for article in articles]
