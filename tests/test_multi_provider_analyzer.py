"""Tests für den unabhängigen Multi-Provider-Abgleich und Quellenvergleich."""

from __future__ import annotations

from avor_smart_attribute_manager.analysis.online_analyzer import (
    run_multi_provider_analysis,
)
from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
    ProviderSpec,
)
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import ComparisonStatus
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules

RULES = AttributeRules(
    rules_by_sachgruppe={"Widerstand": ("Wert", "Toleranz", "Spannung")}
)


class _FakeProvider(ComponentDataProvider):
    def __init__(self, provider_name: str, result: ProviderSearchResult) -> None:
        self._name = provider_name
        self._result = result
        self.calls = 0

    @property
    def name(self) -> str:
        return self._name

    def search_exact(
        self, manufacturer_part_number: str, manufacturer: str | None = None
    ) -> ProviderSearchResult:
        self.calls += 1
        return self._result


def _article() -> Article:
    return Article(
        article_number="A-1",
        sachgruppenklasse="Widerstand",
        attributes={"HerstellerNr": "LM317T", "Hersteller": "Texas Instruments"},
    )


def _mouser_result(**params: str) -> ProviderSearchResult:
    return ProviderSearchResult(
        provider="mouser",
        status=ProviderResponseStatus.OK,
        products=(
            ProviderProduct(
                manufacturer_part_number="LM317T",
                manufacturer="Texas Instruments",
                parameters=dict(params),
            ),
        ),
    )


def _digikey_result(**params: str) -> ProviderSearchResult:
    return ProviderSearchResult(
        provider="digikey-v4",
        status=ProviderResponseStatus.OK,
        products=(
            ProviderProduct(
                manufacturer_part_number="LM317T",
                manufacturer="Texas Instruments",
                parameters=dict(params),
            ),
        ),
    )


def test_providers_run_independently() -> None:
    mouser = _FakeProvider("mouser", _mouser_result(Tolerance="1%"))
    digikey = _FakeProvider("digikey-v4", _digikey_result(Tolerance="1%"))

    analysis, _ = run_multi_provider_analysis([_article()], RULES, [mouser, digikey])

    assert mouser.calls == 1
    assert digikey.calls == 1
    # Ein Status je Provider und Artikel.
    assert len(analysis.statuses) == 2
    providers = {status.provider for status in analysis.statuses}
    assert providers == {"mouser", "digikey-v4"}


def test_sources_agree() -> None:
    mouser = _FakeProvider("mouser", _mouser_result(Tolerance="1%"))
    digikey = _FakeProvider("digikey-v4", _digikey_result(Tolerance="1 %"))

    _, comparisons = run_multi_provider_analysis(
        [_article()], RULES, [mouser, digikey]
    )

    (comparison,) = comparisons
    assert comparison.status is ComparisonStatus.SOURCES_AGREE
    assert set(comparison.providers_with_data) == {"mouser", "digikey-v4"}
    assert "Toleranz" in comparison.agreeing_attributes


def test_sources_conflict() -> None:
    mouser = _FakeProvider("mouser", _mouser_result(Tolerance="1%"))
    digikey = _FakeProvider("digikey-v4", _digikey_result(Tolerance="5%"))

    _, comparisons = run_multi_provider_analysis(
        [_article()], RULES, [mouser, digikey]
    )

    (comparison,) = comparisons
    assert comparison.status is ComparisonStatus.SOURCES_CONFLICT
    assert "Toleranz" in comparison.conflicting_attributes


def test_only_one_provider_has_data() -> None:
    mouser = _FakeProvider("mouser", _mouser_result(Tolerance="1%"))
    digikey = _FakeProvider(
        "digikey-v4",
        ProviderSearchResult(
            provider="digikey-v4", status=ProviderResponseStatus.OK
        ),
    )

    _, comparisons = run_multi_provider_analysis(
        [_article()], RULES, [mouser, digikey]
    )

    (comparison,) = comparisons
    assert comparison.status is ComparisonStatus.ONLY_MOUSER_DATA
    assert comparison.providers_with_data == ("mouser",)


def test_no_technical_data() -> None:
    mouser = _FakeProvider(
        "mouser",
        ProviderSearchResult(provider="mouser", status=ProviderResponseStatus.OK),
    )
    digikey = _FakeProvider(
        "digikey-v4",
        ProviderSearchResult(
            provider="digikey-v4", status=ProviderResponseStatus.OK
        ),
    )

    _, comparisons = run_multi_provider_analysis(
        [_article()], RULES, [mouser, digikey]
    )

    (comparison,) = comparisons
    assert comparison.status is ComparisonStatus.NO_TECHNICAL_DATA


def test_three_structured_sources_agree() -> None:
    mouser = _FakeProvider("mouser", _mouser_result(Tolerance="1%"))
    digikey = _FakeProvider("digikey-v4", _digikey_result(Tolerance="1%"))
    nexar = _FakeProvider(
        "nexar-search-mpn-v1",
        ProviderSearchResult(
            provider="nexar-search-mpn-v1",
            status=ProviderResponseStatus.OK,
            products=(
                ProviderProduct(
                    manufacturer_part_number="LM317T",
                    manufacturer="Texas Instruments",
                    specs=(
                        ProviderSpec(
                            name="tolerance", display_value="1%", unit="%"
                        ),
                    ),
                ),
            ),
        ),
    )

    _, comparisons = run_multi_provider_analysis(
        [_article()], RULES, [mouser, digikey, nexar]
    )

    (comparison,) = comparisons
    assert comparison.status is ComparisonStatus.MULTIPLE_STRUCTURED_SOURCES_AGREE
    assert len(comparison.providers_with_data) == 3
