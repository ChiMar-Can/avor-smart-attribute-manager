"""Attributanalyse – Zusammenspiel von Import und Regelprüfung.

Dieses Modul verbindet den Excel-Import mit der Regelprüfung zu einem
durchgängigen Ablauf: ERP-Export einlesen → Regelwerk laden → je Artikel
prüfen. Es enthält selbst keine Regel- oder Importdetails, sondern orchestriert
lediglich die zuständigen Module.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from avor_smart_attribute_manager.excel.importer import load_articles
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.validation import ArticleValidationResult
from avor_smart_attribute_manager.rules.attribute_rules import (
    AttributeRules,
    load_attribute_rules,
)
from avor_smart_attribute_manager.rules.rule_engine import validate_articles


def analyze_articles(
    articles: Iterable[Article], rules: AttributeRules
) -> list[ArticleValidationResult]:
    """Prüft bereits eingelesene Artikel gegen ein Regelwerk.

    Args:
        articles: Die zu prüfenden Artikel.
        rules: Das anzuwendende Regelwerk.

    Returns:
        Liste der Prüfergebnisse je Artikel.
    """
    return validate_articles(articles, rules)


def analyze_workbook(
    excel_path: Path, rules_path: Path | None = None
) -> list[ArticleValidationResult]:
    """Liest einen ERP-Export ein und prüft ihn gegen das Regelwerk.

    Args:
        excel_path: Pfad zur einzulesenden ERP-Excel-Datei (nur lesend).
        rules_path: Optionaler Pfad zu einer Regelwerksdatei; ohne Angabe wird
            das mitgelieferte Standard-Regelwerk verwendet.

    Returns:
        Liste der Prüfergebnisse je Artikel.
    """
    articles = load_articles(excel_path)
    rules = load_attribute_rules(rules_path)
    return analyze_articles(articles, rules)
