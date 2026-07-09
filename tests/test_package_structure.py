"""Struktur-/Smoke-Tests für das Paketgerüst.

Diese Tests prüfen ausschliesslich, dass die modulare Struktur importierbar
und konsistent ist. Sie enthalten keine Fachlogik und dienen als Absicherung
des Gerüsts, solange die eigentlichen Module noch Platzhalter sind.
"""

from __future__ import annotations

import importlib

import pytest

# Alle Module des Pakets, die ohne optionale Laufzeitabhängigkeiten (z. B.
# PySide6) importierbar sein müssen.
MODULES = [
    "avor_smart_attribute_manager",
    "avor_smart_attribute_manager.app",
    "avor_smart_attribute_manager.config",
    "avor_smart_attribute_manager.config.settings",
    "avor_smart_attribute_manager.models",
    "avor_smart_attribute_manager.models.article",
    "avor_smart_attribute_manager.gui",
    "avor_smart_attribute_manager.gui.main_window",
    "avor_smart_attribute_manager.gui.views",
    "avor_smart_attribute_manager.excel",
    "avor_smart_attribute_manager.excel.importer",
    "avor_smart_attribute_manager.excel.exporter",
    "avor_smart_attribute_manager.excel.columns",
    "avor_smart_attribute_manager.excel.rule_catalog",
    "avor_smart_attribute_manager.analysis",
    "avor_smart_attribute_manager.analysis.attribute_analyzer",
    "avor_smart_attribute_manager.rules",
    "avor_smart_attribute_manager.rules.rule_engine",
    "avor_smart_attribute_manager.rules.attribute_rules",
    "avor_smart_attribute_manager.models.validation",
    "avor_smart_attribute_manager.manufacturers",
    "avor_smart_attribute_manager.manufacturers.manufacturer_data",
    "avor_smart_attribute_manager.datasources",
    "avor_smart_attribute_manager.datasources.base",
    "avor_smart_attribute_manager.ai",
    "avor_smart_attribute_manager.ai.suggestions",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_is_importable(module_name: str) -> None:
    """Jedes Modul des Gerüsts muss importierbar sein."""
    assert importlib.import_module(module_name) is not None


def test_package_exposes_version() -> None:
    """Das Paket stellt eine Versionskennung bereit."""
    import avor_smart_attribute_manager as package

    assert isinstance(package.__version__, str)
