"""Regressionstests für die reale Struktur der Mouser-Search-API-Antwort.

Der echte Ende-zu-Ende-Test (PR #5) hat gezeigt, dass die Mouser Search API in
``ProductAttributes`` **ausschliesslich Verpackungs-/Bestellattribute** liefert
(z. B. ``Verpackung``, ``Standardpackungsmenge``) und die Antwort auf die im
API-Konto hinterlegte Länderseite lokalisiert ist (hier Deutsch). Technische
Kenngrössen (Widerstand, Toleranz, Spannung …) stehen nur im Freitextfeld
``Description``, das laut Regelwerk **nicht** als Attributquelle dienen darf.

Diese Tests fixieren daraus zwei fachliche Zusicherungen:

* Verpackungsattribute werden **nicht** auf ERP-Attribute abgebildet.
* Ein exakter Treffer ohne strukturierte Fachparameter erzeugt **keine**
  (falschen) Attributvorschläge.

Es werden ausschliesslich anonymisierte Beispieldaten verwendet – keine echten
Kunden-, Hersteller- oder Artikeldaten.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from avor_smart_attribute_manager.analysis.attribute_mapping import map_parameters
from avor_smart_attribute_manager.analysis.online_analyzer import run_online_analysis
from avor_smart_attribute_manager.datasources.mouser import MouserProvider
from avor_smart_attribute_manager.datasources.provider import ProviderResponseStatus
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import MatchStatus
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules

# Nachbildung der realen (lokalisierten, verpackungslastigen) Mouser-Antwort.
_PACKAGING_ONLY_PAYLOAD: dict[str, object] = {
    "Errors": [],
    "SearchResults": {
        "Parts": [
            {
                "ManufacturerPartNumber": "GENERIC-RES-0805",
                "Manufacturer": "Example Components",
                "Description": "Dickfilmwiderstände - SMD 1/8Watt 1.4Kohms 1%",
                "Category": "Dickfilmwiderstände - SMD",
                "DataSheetUrl": "",
                "ProductDetailUrl": "https://www.mouser.ch/de/ProductDetail/x",
                "ProductAttributes": [
                    {"AttributeName": "Verpackung", "AttributeValue": "Reel"},
                    {"AttributeName": "Verpackung", "AttributeValue": "Cut Tape"},
                    {"AttributeName": "Standardpackungsmenge", "AttributeValue": "5000"},
                ],
            }
        ]
    },
}


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _FakeSession:
    def __init__(self, handler: Callable[[], _FakeResponse]) -> None:
        self._handler = handler
        self.calls = 0

    def post(
        self, url: str, json: Any = None, timeout: float | None = None
    ) -> _FakeResponse:
        self.calls += 1
        return self._handler()


def _provider() -> MouserProvider:
    session = _FakeSession(lambda: _FakeResponse(200, _PACKAGING_ONLY_PAYLOAD))
    return MouserProvider(
        "dummy-key",
        session=session,  # type: ignore[arg-type]
        max_retries=0,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def test_provider_returns_only_packaging_attributes() -> None:
    result = _provider().search_exact("GENERIC-RES-0805")

    assert result.status is ProviderResponseStatus.OK
    (product,) = result.products
    # Nur Verpackungsattribute – keine technischen Kenngrössen.
    assert set(product.parameters) == {"Verpackung", "Standardpackungsmenge"}


def test_localized_packaging_names_are_not_mapped() -> None:
    mapped = map_parameters(
        {"Verpackung": "Reel", "Standardpackungsmenge": "5000"},
        "Widerstand",
        allowed_attributes={"Wert", "Toleranz", "Spannung"},
    )
    assert mapped == {}


def test_exact_match_without_technical_params_yields_no_suggestions() -> None:
    rules = AttributeRules(
        rules_by_sachgruppe={"Widerstand": ("Wert", "Toleranz", "Spannung")}
    )
    article = Article(
        article_number="ANON-1",
        sachgruppenklasse="Widerstand",
        attributes={
            "HerstellerNr": "GENERIC-RES-0805",
            "Hersteller": "Example Components",
        },
    )

    analysis = run_online_analysis([article], rules, _provider())

    assert analysis.statuses[0].match_status is MatchStatus.EXACT_MATCH
    # Kein strukturierter Fachparameter -> kein (falscher) Vorschlag.
    assert analysis.suggestions == []
