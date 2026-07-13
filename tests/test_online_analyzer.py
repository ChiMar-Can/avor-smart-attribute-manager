"""Tests für die Online-Abgleich-Orchestrierung."""

from __future__ import annotations

from pathlib import Path

from avor_smart_attribute_manager.analysis.online_analyzer import run_online_analysis
from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import (
    MatchConfidence,
    MatchStatus,
    SuggestionAction,
)
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules

RULES = AttributeRules(
    rules_by_sachgruppe={"Widerstand": ("Wert", "Toleranz", "Spannung")}
)


class _FakeProvider(ComponentDataProvider):
    def __init__(self, result: ProviderSearchResult) -> None:
        self._result = result
        self.calls = 0

    @property
    def name(self) -> str:
        return "mouser"

    def search_exact(
        self, manufacturer_part_number: str, manufacturer: str | None = None
    ) -> ProviderSearchResult:
        self.calls += 1
        return self._result


def _article(**attributes: object) -> Article:
    base = {"HerstellerNr": "LM317T", "Hersteller": "Texas Instruments"}
    base.update(attributes)
    return Article(
        article_number="A-1",
        sachgruppenklasse="Widerstand",
        attributes=base,
    )


def _result(*products: ProviderProduct) -> ProviderSearchResult:
    return ProviderSearchResult(
        provider="mouser", status=ProviderResponseStatus.OK, products=products
    )


def _product(
    mpn: str = "LM317T",
    manufacturer: str = "Texas Instruments",
    **params: str,
) -> ProviderProduct:
    return ProviderProduct(
        manufacturer_part_number=mpn,
        manufacturer=manufacturer,
        product_url="https://example.com/p",
        datasheet_url="https://example.com/ds",
        parameters=dict(params),
    )


def test_exact_match_with_manufacturer_is_high_confidence() -> None:
    provider = _FakeProvider(_result(_product(Tolerance="1%")))
    article = _article()  # kein Toleranz-Wert im ERP

    analysis = run_online_analysis([article], RULES, provider)

    status = analysis.statuses[0]
    assert status.match_status is MatchStatus.EXACT_MATCH
    assert len(analysis.suggestions) == 1
    suggestion = analysis.suggestions[0]
    assert suggestion.attribute == "Toleranz"
    assert suggestion.confidence is MatchConfidence.HOCH
    assert suggestion.action is SuggestionAction.ERGAENZEN


def test_exact_match_without_erp_manufacturer_is_medium() -> None:
    provider = _FakeProvider(_result(_product(Tolerance="1%")))
    article = _article(Hersteller=None)

    analysis = run_online_analysis([article], RULES, provider)

    assert analysis.statuses[0].match_status is MatchStatus.EXACT_MATCH
    assert analysis.suggestions[0].confidence is MatchConfidence.MITTEL


def test_manufacturer_mismatch() -> None:
    provider = _FakeProvider(_result(_product(manufacturer="Other Corp", Tolerance="1%")))
    analysis = run_online_analysis([_article()], RULES, provider)

    status = analysis.statuses[0]
    assert status.match_status is MatchStatus.MANUFACTURER_MISMATCH
    # Vorschläge (falls vorhanden) nur mit niedriger Konfidenz.
    assert all(
        s.confidence is MatchConfidence.NIEDRIG for s in analysis.suggestions
    )


def test_multiple_exact_matches_only_consensus() -> None:
    provider = _FakeProvider(
        _result(
            _product(Tolerance="1%", **{"Voltage Rating": "50V"}),
            _product(Tolerance="1%", **{"Voltage Rating": "25V"}),
        )
    )
    analysis = run_online_analysis([_article()], RULES, provider)

    status = analysis.statuses[0]
    assert status.match_status is MatchStatus.MULTIPLE_EXACT_MATCHES
    attributes = {s.attribute for s in analysis.suggestions}
    # Toleranz stimmt überein → Vorschlag; Spannung weicht ab → kein Vorschlag.
    assert attributes == {"Toleranz"}
    assert all(s.confidence is MatchConfidence.NIEDRIG for s in analysis.suggestions)


def test_no_exact_match() -> None:
    provider = _FakeProvider(_result(_product(mpn="DIFFERENT")))
    analysis = run_online_analysis([_article()], RULES, provider)

    assert analysis.statuses[0].match_status is MatchStatus.NO_EXACT_MATCH
    assert analysis.suggestions == []


def test_no_mpn_is_reported() -> None:
    provider = _FakeProvider(_result())
    article = _article(HerstellerNr=None)

    analysis = run_online_analysis([article], RULES, provider)

    assert analysis.statuses[0].match_status is MatchStatus.NO_MPN
    assert provider.calls == 0


def test_api_error_is_isolated_per_article() -> None:
    provider = _FakeProvider(
        ProviderSearchResult(
            provider="mouser",
            status=ProviderResponseStatus.API_ERROR,
            error_message="boom",
        )
    )
    analysis = run_online_analysis([_article(), _article()], RULES, provider)

    assert all(s.match_status is MatchStatus.API_ERROR for s in analysis.statuses)
    assert len(analysis.statuses) == 2


def test_rate_limited_status() -> None:
    provider = _FakeProvider(
        ProviderSearchResult(
            provider="mouser", status=ProviderResponseStatus.RATE_LIMITED
        )
    )
    analysis = run_online_analysis([_article()], RULES, provider)
    assert analysis.statuses[0].match_status is MatchStatus.RATE_LIMITED


def test_cache_hit_avoids_second_call(tmp_path: Path) -> None:
    provider = _FakeProvider(_result(_product(Tolerance="1%")))
    cache = SearchCache(tmp_path)

    run_online_analysis([_article()], RULES, provider, cache)
    run_online_analysis([_article()], RULES, provider, cache)

    assert provider.calls == 1


def test_existing_value_confirmed_not_overwritten() -> None:
    provider = _FakeProvider(_result(_product(Tolerance="1%")))
    article = _article(Toleranz="1 %")

    analysis = run_online_analysis([article], RULES, provider)

    suggestion = analysis.suggestions[0]
    assert suggestion.action is SuggestionAction.BESTAETIGT
    assert suggestion.erp_value == "1 %"  # ERP-Wert bleibt unverändert erhalten


def test_conflicting_value_is_flagged() -> None:
    provider = _FakeProvider(_result(_product(Tolerance="1%")))
    article = _article(Toleranz="5%")

    analysis = run_online_analysis([article], RULES, provider)

    suggestion = analysis.suggestions[0]
    assert suggestion.action is SuggestionAction.KONFLIKT_PRUEFEN
    assert suggestion.erp_value == "5%"


def test_mapping_only_allowed_attributes() -> None:
    # "Dielectric" ist für Widerstand nicht erlaubt → kein Vorschlag.
    provider = _FakeProvider(_result(_product(**{"Dielectric": "X7R"})))
    analysis = run_online_analysis([_article()], RULES, provider)

    assert analysis.suggestions == []
