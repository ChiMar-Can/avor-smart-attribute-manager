"""Tests für die Regelauswertung je Artikel."""

from __future__ import annotations

from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.validation import CheckStatus
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules
from avor_smart_attribute_manager.rules.rule_engine import (
    validate_article,
    validate_articles,
)

_RULES = AttributeRules(
    rules_by_sachgruppe={
        "WIDERSTAND": frozenset({"Dimension", "Widerstandattribut"}),
    }
)


def _article(sachgruppe: str, attributes: dict[str, object]) -> Article:
    return Article(
        article_number="A-1",
        sachgruppenklasse=sachgruppe,
        attributes=attributes,
    )


def test_unknown_sachgruppe_is_flagged() -> None:
    result = validate_article(_article("UNBEKANNT", {"Dimension": "0805"}), _RULES)

    assert result.status is CheckStatus.UNKNOWN_SACHGRUPPE
    assert result.allowed_attributes == ()
    assert result.missing_attributes == ()
    assert result.disallowed_filled_attributes == ()


def test_known_sachgruppe_all_attributes_present_is_ok() -> None:
    result = validate_article(
        _article("WIDERSTAND", {"Dimension": "0805", "Widerstandattribut": "10k"}),
        _RULES,
    )

    assert result.status is CheckStatus.OK
    assert result.allowed_attributes == ("Dimension", "Widerstandattribut")
    assert result.missing_attributes == ()
    assert result.disallowed_filled_attributes == ()


def test_missing_allowed_attribute_is_detected() -> None:
    result = validate_article(
        _article("WIDERSTAND", {"Dimension": "0805", "Widerstandattribut": None}),
        _RULES,
    )

    assert result.status is CheckStatus.ISSUES_FOUND
    assert result.missing_attributes == ("Widerstandattribut",)


def test_disallowed_filled_attribute_is_detected() -> None:
    result = validate_article(
        _article(
            "WIDERSTAND",
            {"Dimension": "0805", "Widerstandattribut": "10k", "Feeder": "8mm"},
        ),
        _RULES,
    )

    assert result.status is CheckStatus.ISSUES_FOUND
    assert result.disallowed_filled_attributes == ("Feeder",)


def test_validate_articles_preserves_order() -> None:
    articles = [
        _article("WIDERSTAND", {"Dimension": "0805", "Widerstandattribut": "10k"}),
        _article("UNBEKANNT", {}),
    ]

    results = validate_articles(articles, _RULES)

    assert [result.status for result in results] == [
        CheckStatus.OK,
        CheckStatus.UNKNOWN_SACHGRUPPE,
    ]
