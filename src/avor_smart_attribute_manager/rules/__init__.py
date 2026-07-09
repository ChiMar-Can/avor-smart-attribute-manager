"""Regelprüfung.

Enthält die Prüfung der Daten gegen definierbare Regeln (z. B. Pflichtfelder,
Formatvorgaben, erlaubte Wertebereiche, Namenskonventionen).

Verantwortung:

* Verwaltung eines Satzes von Regeln.
* Anwendung der Regeln auf die Daten und Erzeugung nachvollziehbarer
  Regelverstösse als Vorschläge zur Korrektur.

Die Regeln sollen später konfigurierbar/erweiterbar sein, ohne den Kerncode zu
ändern (offene Erweiterbarkeit). Es werden hier keine konkreten Regeln
erfunden.
"""

from __future__ import annotations

from avor_smart_attribute_manager.rules.attribute_rules import (
    AttributeRules,
    InvalidRulesError,
    load_attribute_rules,
    rules_document_from_mapping,
)
from avor_smart_attribute_manager.rules.rule_engine import (
    validate_article,
    validate_articles,
)

__all__ = [
    "AttributeRules",
    "InvalidRulesError",
    "load_attribute_rules",
    "rules_document_from_mapping",
    "validate_article",
    "validate_articles",
]
