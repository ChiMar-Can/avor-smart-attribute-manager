"""Attributanalyse – Zusammenspiel von Import und Regelprüfung.

Dieses Modul verbindet den Excel-Import mit der Regelprüfung zu einem
durchgängigen Ablauf: ERP-Export einlesen → Regelwerk laden → je Artikel
prüfen. Es enthält selbst keine Regel- oder Importdetails, sondern orchestriert
lediglich die zuständigen Module.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from avor_smart_attribute_manager.analysis.online_analyzer import (
    run_multi_provider_analysis,
)
from avor_smart_attribute_manager.config.settings import (
    DIGIKEY_PROVIDER,
    MOUSER_PROVIDER,
    NEXAR_PROVIDER,
    Settings,
    load_settings,
)
from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.digikey import DigiKeyProvider
from avor_smart_attribute_manager.datasources.mouser import MouserProvider
from avor_smart_attribute_manager.datasources.nexar import NexarProvider
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
from avor_smart_attribute_manager.models.online import OnlineAnalysis, ProviderComparison
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


def build_provider(settings: Settings, name: str) -> ComponentDataProvider:
    """Erzeugt einen einzelnen Provider anhand seines Namens.

    Args:
        settings: Anwendungseinstellungen mit den Zugangsdaten.
        name: Providername (``"mouser"``, ``"digikey"`` oder ``"nexar"``).

    Returns:
        Ein konfigurierter :class:`ComponentDataProvider`.

    Raises:
        MissingApiKeyError: Wenn die benötigten Zugangsdaten fehlen.
        ValueError: Wenn der Providername unbekannt ist.
    """
    if name == DIGIKEY_PROVIDER:
        return DigiKeyProvider(
            settings.digikey_client_id or "",
            settings.digikey_client_secret or "",
            version=settings.digikey_api_version,
            base_url=settings.digikey_base_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
    if name == NEXAR_PROVIDER:
        return NexarProvider(
            settings.nexar_client_id,
            settings.nexar_client_secret,
            access_token=settings.nexar_access_token,
            token_url=settings.nexar_token_url,
            graphql_url=settings.nexar_graphql_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
    if name == MOUSER_PROVIDER:
        return MouserProvider(
            settings.mouser_api_key or "",
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
    raise ValueError(f"Unbekannter Provider: '{name}'.")


def build_default_provider(settings: Settings) -> ComponentDataProvider:
    """Erzeugt den konfigurierten Standard-Provider aus den Einstellungen.

    Die Auswahl (Mouser, DigiKey oder Nexar) erfolgt über ``settings.provider``
    und ist damit nicht in der Fachlogik fest verdrahtet.

    Args:
        settings: Anwendungseinstellungen mit Provider-Auswahl und Zugangsdaten.

    Returns:
        Ein konfigurierter :class:`ComponentDataProvider`.

    Raises:
        MissingApiKeyError: Wenn die benötigten Zugangsdaten fehlen.
    """
    if settings.provider in (DIGIKEY_PROVIDER, NEXAR_PROVIDER):
        return build_provider(settings, settings.provider)
    return build_provider(settings, MOUSER_PROVIDER)


def build_providers(
    settings: Settings, names: Sequence[str]
) -> list[ComponentDataProvider]:
    """Erzeugt mehrere Provider anhand ihrer Namen (Reihenfolge bleibt erhalten).

    Args:
        settings: Anwendungseinstellungen mit den Zugangsdaten.
        names: Providernamen; Duplikate werden unter Beibehaltung der
            Reihenfolge entfernt.

    Returns:
        Liste konfigurierter Provider.

    Raises:
        MissingApiKeyError: Wenn die Zugangsdaten eines Providers fehlen.
        ValueError: Wenn ein Providername unbekannt ist.
    """
    unique = list(dict.fromkeys(names))
    return [build_provider(settings, name) for name in unique]


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
    comparisons: list[ProviderComparison] = field(default_factory=list)


def analyze_and_export_with_online(
    excel_path: Path,
    output_path: Path | None = None,
    rules_path: Path | None = None,
    *,
    provider: ComponentDataProvider | None = None,
    providers: Sequence[ComponentDataProvider] | None = None,
    settings: Settings | None = None,
) -> OnlineAnalysisExport:
    """Analysiert einen ERP-Export, gleicht online ab und schreibt eine Datei.

    Die Eingabedatei wird ausschliesslich gelesen. Zusätzlich zu Analyse und
    Zusammenfassung enthält die Ausgabe die Blätter ``Online_Vorschlaege`` und
    ``Online_Abgleich`` sowie – bei mehreren Providern – ``Provider_Vergleich``.
    Bestehende ERP-Werte werden niemals verändert.

    Args:
        excel_path: Pfad zur einzulesenden ERP-Excel-Datei (nur lesend).
        output_path: Optionaler Zielpfad; ohne Angabe wird
            ``<Dateiname>_analyse.xlsx`` verwendet.
        rules_path: Optionaler Pfad zu einer Regelwerksdatei.
        provider: Optionaler einzelner Provider (Standard aus den Einstellungen).
        providers: Optionale Liste mehrerer Provider (hat Vorrang vor
            ``provider``). Ermöglicht den parallelen, unabhängigen Abgleich über
            mehrere Datenquellen inkl. Quellenvergleich.
        settings: Optionale Einstellungen (Standard: aus Umgebung/``.env``).

    Returns:
        Ein :class:`OnlineAnalysisExport` mit Ausgabepfad, Prüfergebnissen,
        Online-Abgleich und (bei mehreren Providern) Quellenvergleich.

    Raises:
        MissingApiKeyError: Wenn kein Provider übergeben wird und die
            Zugangsdaten fehlen.
    """
    effective_settings = settings if settings is not None else load_settings()
    original = read_workbook(excel_path)
    articles = to_articles(normalize_dataframe(original))
    rules = load_attribute_rules(rules_path)
    results = analyze_articles(articles, rules)

    if providers is not None:
        active_providers: list[ComponentDataProvider] = list(providers)
    elif provider is not None:
        active_providers = [provider]
    else:
        active_providers = [build_default_provider(effective_settings)]

    cache = (
        SearchCache(effective_settings.cache_dir, effective_settings.cache_ttl_seconds)
        if effective_settings.use_cache
        else None
    )
    online, comparisons = run_multi_provider_analysis(
        articles, rules, active_providers, cache
    )
    # Der Quellenvergleich ist nur bei mehreren Providern aussagekräftig.
    export_comparisons = comparisons if len(active_providers) > 1 else []
    target = export_analysis_with_online(
        original,
        results,
        online.suggestions,
        online.statuses,
        excel_path,
        output_path,
        comparisons=export_comparisons,
    )
    return OnlineAnalysisExport(
        output_path=target,
        results=results,
        online=online,
        comparisons=export_comparisons,
    )
