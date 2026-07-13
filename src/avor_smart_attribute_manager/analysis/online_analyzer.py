"""Online-Abgleich der ERP-Attribute anhand der Herstellerteilenummer.

Ablauf je Artikel:

1. Herstellerteilenummer (und ggf. Hersteller) aus dem Artikel lesen.
2. Herstellerteilenummer **nur technisch** bereinigen (keine Inhaltsänderung).
3. Datenquelle abfragen (mit lokalem Cache), Fehler robust behandeln.
4. Exakten Abgleich durchführen (MPN + ggf. Hersteller).
5. Strukturierte Quellparameter sachgruppenabhängig auf erlaubte ERP-Attribute
   abbilden und daraus nachvollziehbare Vorschläge erzeugen.

Grundregeln: Bestehende ERP-Werte werden **niemals** verändert. Die manuell
gepflegte ERP-Benennung wird **nicht** als Quelle verwendet. Bei mehreren oder
unsicheren Treffern wird **kein** Wert automatisch als sicher markiert.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from avor_smart_attribute_manager.analysis.attribute_mapping import map_parameters
from avor_smart_attribute_manager.analysis.value_comparison import values_match
from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.normalization import (
    clean_part_number,
    manufacturer_key,
    part_number_key,
)
from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)
from avor_smart_attribute_manager.excel.columns import (
    MANUFACTURER_COLUMN,
    MANUFACTURER_PART_NUMBER_COLUMN,
    SACHGRUPPE_LABEL_COLUMN,
)
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
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules

#: Callable-Typ für die Zeitquelle (injizierbar für Tests).
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    """Liefert den aktuellen Zeitpunkt in UTC."""
    return datetime.now(UTC)


def _attribute_str(article: Article, column: str) -> str | None:
    """Liest einen Attributwert als bereinigten String (oder ``None``)."""
    value = article.attributes.get(column)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _display_sachgruppe(article: Article) -> str:
    """Ermittelt die anzuzeigende Sachgruppe (Anzeigespalte, sonst Klasse)."""
    return _attribute_str(article, SACHGRUPPE_LABEL_COLUMN) or article.sachgruppenklasse


def _build_product_info(
    article: Article,
    requested_mpn: str,
    requested_manufacturer: str | None,
    product: ProviderProduct,
    provider: str,
    retrieved_at: datetime,
    match_status: MatchStatus,
    confidence: MatchConfidence | None,
) -> ProductInfo:
    """Überführt einen Provider-Treffer in das neutrale Produktdatenmodell."""
    return ProductInfo(
        erp_article_number=article.article_number,
        requested_mpn=requested_mpn,
        requested_manufacturer=requested_manufacturer,
        found_mpn=product.manufacturer_part_number,
        found_manufacturer=product.manufacturer,
        description=product.description,
        category=product.category,
        datasheet_url=product.datasheet_url,
        product_url=product.product_url,
        raw_attributes=dict(product.parameters),
        provider=provider,
        retrieved_at=retrieved_at,
        match_status=match_status,
        match_confidence=confidence,
    )


def _consensus_mapping(
    products: Sequence[ProviderProduct],
    sachgruppe: str,
    allowed_attributes: tuple[str, ...],
) -> dict[str, str]:
    """Ermittelt nur die Attribute, in denen alle Treffer übereinstimmen.

    Damit wird bei mehreren/unsicheren Treffern nichts geraten: Ein Attribut
    wird nur übernommen, wenn jeder Treffer denselben (normalisiert gleichen)
    Wert liefert.
    """
    per_product = [
        map_parameters(product.parameters, sachgruppe, allowed_attributes)
        for product in products
    ]
    if not per_product:
        return {}

    consensus: dict[str, str] = {}
    for attribute, value in per_product[0].items():
        if all(
            attribute in mapping and values_match(mapping[attribute], value)
            for mapping in per_product[1:]
        ):
            consensus[attribute] = value
    return consensus


def _suggestions_for(
    article: Article,
    sachgruppe_label: str,
    mapped: dict[str, str],
    product: ProviderProduct,
    provider: str,
    match_status: MatchStatus,
    confidence: MatchConfidence,
) -> list[AttributeSuggestion]:
    """Erzeugt Vorschläge aus bereits gemappten (erlaubten) Attributwerten."""
    suggestions: list[AttributeSuggestion] = []
    for attribute, suggested_value in mapped.items():
        erp_value = _attribute_str(article, attribute)
        if erp_value is None:
            action = SuggestionAction.ERGAENZEN
            reason = "ERP-Wert leer, Online-Wert vorhanden."
        elif values_match(erp_value, suggested_value):
            action = SuggestionAction.BESTAETIGT
            reason = "ERP-Wert stimmt mit Online-Wert überein (normalisiert)."
        else:
            action = SuggestionAction.KONFLIKT_PRUEFEN
            reason = "ERP-Wert und Online-Wert weichen ab – bitte prüfen."

        suggestions.append(
            AttributeSuggestion(
                article_number=article.article_number,
                sachgruppe=sachgruppe_label,
                attribute=attribute,
                erp_value=erp_value,
                suggested_value=suggested_value,
                action=action,
                provider=provider,
                source_mpn=product.manufacturer_part_number,
                source_manufacturer=product.manufacturer,
                match_status=match_status,
                confidence=confidence,
                product_url=product.product_url,
                datasheet_url=product.datasheet_url,
                reason=reason,
            )
        )
    return suggestions


def _match_products(
    products: Sequence[ProviderProduct],
    mpn: str,
    manufacturer: str | None,
) -> tuple[MatchStatus, list[ProviderProduct]]:
    """Führt den exakten Abgleich durch und liefert Status + passende Treffer."""
    mpn_target = part_number_key(mpn)
    mpn_matches = [
        product
        for product in products
        if product.manufacturer_part_number is not None
        and part_number_key(product.manufacturer_part_number) == mpn_target
    ]
    if not mpn_matches:
        return MatchStatus.NO_EXACT_MATCH, []

    if manufacturer:
        target = manufacturer_key(manufacturer)
        exact = [
            product
            for product in mpn_matches
            if product.manufacturer is not None
            and manufacturer_key(product.manufacturer) == target
        ]
        if not exact:
            return MatchStatus.MANUFACTURER_MISMATCH, mpn_matches
        status = (
            MatchStatus.EXACT_MATCH
            if len(exact) == 1
            else MatchStatus.MULTIPLE_EXACT_MATCHES
        )
        return status, exact

    status = (
        MatchStatus.EXACT_MATCH
        if len(mpn_matches) == 1
        else MatchStatus.MULTIPLE_EXACT_MATCHES
    )
    return status, mpn_matches


def _analyze_article(
    article: Article,
    rules: AttributeRules,
    provider: ComponentDataProvider,
    cache: SearchCache | None,
    clock: Clock,
) -> tuple[ArticleOnlineStatus, list[AttributeSuggestion]]:
    """Führt den Online-Abgleich für einen einzelnen Artikel durch."""
    sachgruppe_label = _display_sachgruppe(article)
    manufacturer = _attribute_str(article, MANUFACTURER_COLUMN)
    raw_mpn = _attribute_str(article, MANUFACTURER_PART_NUMBER_COLUMN)

    def status(
        match_status: MatchStatus,
        *,
        mpn: str | None = None,
        count: int = 0,
        message: str | None = None,
        product: ProductInfo | None = None,
    ) -> ArticleOnlineStatus:
        return ArticleOnlineStatus(
            article_number=article.article_number,
            sachgruppe=sachgruppe_label,
            manufacturer=manufacturer,
            manufacturer_part_number=mpn,
            provider=provider.name,
            match_status=match_status,
            match_count=count,
            message=message,
            product=product,
        )

    if raw_mpn is None:
        return (
            status(MatchStatus.NO_MPN, message="Keine Herstellerteilenummer vorhanden."),
            [],
        )

    mpn = clean_part_number(raw_mpn)
    if not mpn:
        return (
            status(MatchStatus.NO_MPN, message="Herstellerteilenummer ist leer."),
            [],
        )

    result: ProviderSearchResult | None = None
    if cache is not None:
        result = cache.get(provider.name, mpn, manufacturer)
    if result is None:
        result = provider.search_exact(mpn, manufacturer)
        if cache is not None:
            cache.set(provider.name, mpn, manufacturer, result)

    if result.status is ProviderResponseStatus.RATE_LIMITED:
        return status(MatchStatus.RATE_LIMITED, mpn=mpn, message=result.error_message), []
    if result.status is ProviderResponseStatus.API_ERROR:
        return status(MatchStatus.API_ERROR, mpn=mpn, message=result.error_message), []

    match_status, matched = _match_products(result.products, mpn, manufacturer)
    if not matched:
        return status(MatchStatus.NO_EXACT_MATCH, mpn=mpn), []

    allowed = rules.allowed_for(article.sachgruppenklasse)
    primary = matched[0]

    if match_status is MatchStatus.EXACT_MATCH:
        confidence = MatchConfidence.HOCH if manufacturer else MatchConfidence.MITTEL
        mapped = map_parameters(primary.parameters, article.sachgruppenklasse, allowed)
    else:
        confidence = MatchConfidence.NIEDRIG
        mapped = _consensus_mapping(matched, article.sachgruppenklasse, allowed)

    product_info = _build_product_info(
        article,
        mpn,
        manufacturer,
        primary,
        provider.name,
        clock(),
        match_status,
        confidence,
    )
    suggestions = _suggestions_for(
        article,
        sachgruppe_label,
        mapped,
        primary,
        provider.name,
        match_status,
        confidence,
    )
    return (
        status(match_status, mpn=mpn, count=len(matched), product=product_info),
        suggestions,
    )


def run_online_analysis(
    articles: Sequence[Article],
    rules: AttributeRules,
    provider: ComponentDataProvider,
    cache: SearchCache | None = None,
    clock: Clock = _utc_now,
) -> OnlineAnalysis:
    """Führt den Online-Abgleich für mehrere Artikel durch.

    Fehler einzelner Artikel (API-Fehler, Rate-Limit) unterbrechen die
    Verarbeitung nicht; sie werden pro Artikel im Status dokumentiert.

    Args:
        articles: Die zu prüfenden Artikel (in Zeilenreihenfolge).
        rules: Das Regelwerk (bestimmt erlaubte Attribute je Sachgruppe).
        provider: Die zu nutzende Datenquelle.
        cache: Optionaler lokaler Cache.
        clock: Zeitquelle (injizierbar für Tests).

    Returns:
        Eine :class:`OnlineAnalysis` mit einem Status je Artikel und allen
        erzeugten Vorschlägen.
    """
    statuses: list[ArticleOnlineStatus] = []
    suggestions: list[AttributeSuggestion] = []
    for article in articles:
        article_status, article_suggestions = _analyze_article(
            article, rules, provider, cache, clock
        )
        statuses.append(article_status)
        suggestions.extend(article_suggestions)
    return OnlineAnalysis(statuses=statuses, suggestions=suggestions)
