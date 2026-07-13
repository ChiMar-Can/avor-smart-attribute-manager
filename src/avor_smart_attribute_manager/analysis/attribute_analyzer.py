"""Attributanalyse – Zusammenspiel von Import und Regelprüfung.

Dieses Modul verbindet den Excel-Import mit der Regelprüfung zu einem
durchgängigen Ablauf: ERP-Export einlesen → Regelwerk laden → je Artikel
prüfen. Es enthält selbst keine Regel- oder Importdetails, sondern orchestriert
lediglich die zuständigen Module.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from avor_smart_attribute_manager.analysis.online_analyzer import run_online_analysis
from avor_smart_attribute_manager.config.settings import (
    DIGIKEY_PROVIDER,
    Settings,
    load_settings,
)
from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.digikey import DigiKeyProvider
from avor_smart_attribute_manager.datasources.mouser import MouserProvider
from avor_smart_attribute_manager.datasources.provider import ComponentDataProvider
from avor_smart_attribute_manager.excel.exporter import (
    export_analysis,
    export_analysis_with_online,
)
from avor_smart_attribute_manager.excel.importer import (
    load_articles,
    normalize_dataframe,
    read_workbook,
    to_articles,
)
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import OnlineAnalysis
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


@dataclass(frozen=True)
class AnalysisExport:
    """Ergebnis eines Analyse- und Exportlaufs.

    Attributes:
        output_path: Pfad der geschriebenen Analysedatei.
        results: Prüfergebnisse je Artikel (in Zeilenreihenfolge).
    """

    output_path: Path
    results: list[ArticleValidationResult]


def analyze_and_export(
    excel_path: Path,
    output_path: Path | None = None,
    rules_path: Path | None = None,
) -> AnalysisExport:
    """Analysiert einen ERP-Export und schreibt die Ergebnisse als neue Datei.

    Die Eingabedatei wird ausschliesslich gelesen. Die Ausgabe enthält alle
    Originalspalten sowie die Analysespalten und ein Zusammenfassungsblatt.

    Args:
        excel_path: Pfad zur einzulesenden ERP-Excel-Datei (nur lesend).
        output_path: Optionaler Zielpfad; ohne Angabe wird
            ``<Dateiname>_analyse.xlsx`` verwendet.
        rules_path: Optionaler Pfad zu einer Regelwerksdatei; ohne Angabe wird
            das mitgelieferte Standard-Regelwerk verwendet.

    Returns:
        Ein :class:`AnalysisExport` mit dem Ausgabepfad und den Prüfergebnissen.
    """
    original = read_workbook(excel_path)
    articles = to_articles(normalize_dataframe(original))
    rules = load_attribute_rules(rules_path)
    results = analyze_articles(articles, rules)
    target = export_analysis(original, results, excel_path, output_path)
    return AnalysisExport(output_path=target, results=results)


def build_default_provider(settings: Settings) -> ComponentDataProvider:
    """Erzeugt den konfigurierten Provider aus den Einstellungen.

    Die Auswahl (Mouser oder DigiKey) erfolgt über ``settings.provider`` und ist
    damit nicht in der Fachlogik fest verdrahtet. Bei DigiKey wird die ebenfalls
    konfigurierbare API-Version (V3/V4) verwendet.

    Args:
        settings: Anwendungseinstellungen mit Provider-Auswahl und Zugangsdaten.

    Returns:
        Ein konfigurierter :class:`ComponentDataProvider`.

    Raises:
        MissingApiKeyError: Wenn die benötigten Zugangsdaten fehlen.
    """
    if settings.provider == DIGIKEY_PROVIDER:
        return DigiKeyProvider(
            settings.digikey_client_id or "",
            settings.digikey_client_secret or "",
            version=settings.digikey_api_version,
            base_url=settings.digikey_base_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
    return MouserProvider(
        settings.mouser_api_key or "",
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        backoff_seconds=settings.backoff_seconds,
    )


@dataclass(frozen=True)
class OnlineAnalysisExport:
    """Ergebnis eines Analyse-, Online-Abgleich- und Exportlaufs.

    Attributes:
        output_path: Pfad der geschriebenen Analysedatei.
        results: Prüfergebnisse je Artikel (in Zeilenreihenfolge).
        online: Ergebnis des Online-Abgleichs (Status je Artikel + Vorschläge).
    """

    output_path: Path
    results: list[ArticleValidationResult]
    online: OnlineAnalysis


def analyze_and_export_with_online(
    excel_path: Path,
    output_path: Path | None = None,
    rules_path: Path | None = None,
    *,
    provider: ComponentDataProvider | None = None,
    settings: Settings | None = None,
) -> OnlineAnalysisExport:
    """Analysiert einen ERP-Export, gleicht online ab und schreibt eine Datei.

    Die Eingabedatei wird ausschliesslich gelesen. Zusätzlich zu Analyse und
    Zusammenfassung enthält die Ausgabe die Blätter ``Online_Vorschlaege`` und
    ``Online_Abgleich``. Bestehende ERP-Werte werden niemals verändert.

    Args:
        excel_path: Pfad zur einzulesenden ERP-Excel-Datei (nur lesend).
        output_path: Optionaler Zielpfad; ohne Angabe wird
            ``<Dateiname>_analyse.xlsx`` verwendet.
        rules_path: Optionaler Pfad zu einer Regelwerksdatei.
        provider: Optionaler Provider (Standard: Mouser aus den Einstellungen).
        settings: Optionale Einstellungen (Standard: aus Umgebung/``.env``).

    Returns:
        Ein :class:`OnlineAnalysisExport` mit Ausgabepfad, Prüfergebnissen und
        Online-Abgleich.

    Raises:
        MissingApiKeyError: Wenn kein Provider übergeben wird und kein
            API-Schlüssel gesetzt ist.
    """
    effective_settings = settings if settings is not None else load_settings()
    original = read_workbook(excel_path)
    articles = to_articles(normalize_dataframe(original))
    rules = load_attribute_rules(rules_path)
    results = analyze_articles(articles, rules)

    active_provider = (
        provider if provider is not None else build_default_provider(effective_settings)
    )
    cache = (
        SearchCache(effective_settings.cache_dir, effective_settings.cache_ttl_seconds)
        if effective_settings.use_cache
        else None
    )
    online = run_online_analysis(articles, rules, active_provider, cache)
    target = export_analysis_with_online(
        original, results, online.suggestions, online.statuses, excel_path, output_path
    )
    return OnlineAnalysisExport(output_path=target, results=results, online=online)
