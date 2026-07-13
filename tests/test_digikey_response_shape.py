"""End-to-End-Zusicherungen für die (strukturierte) DigiKey-Antwortform.

Im Gegensatz zur Mouser Search API (die strukturiert nur Verpackungsattribute
liefert, siehe ``docs/mouser_e2e_report.md``) stellt die DigiKey Product
Information API strukturierte **technische** Parameter (``Parameters``) bereit.
Diese Tests fixieren anhand anonymisierter Beispieldaten, dass solche Parameter
sachgruppenabhängig auf erlaubte ERP-Attribute abgebildet werden und daraus
nachvollziehbare Vorschläge entstehen.

Es werden ausschliesslich anonymisierte Beispieldaten verwendet – keine echten
Kunden-, Hersteller- oder Artikeldaten und keine echten API-Aufrufe.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from avor_smart_attribute_manager.analysis.online_analyzer import run_online_analysis
from avor_smart_attribute_manager.datasources.digikey import (
    DigiKeyApiVersion,
    DigiKeyProvider,
)
from avor_smart_attribute_manager.models.article import Article
from avor_smart_attribute_manager.models.online import (
    MatchStatus,
    SuggestionAction,
)
from avor_smart_attribute_manager.rules.attribute_rules import AttributeRules

# Anonymisierter, strukturierter DigiKey-V4-Datensatz (Widerstand).
_V4_PAYLOAD: dict[str, object] = {
    "Products": [
        {
            "ManufacturerProductNumber": "GENERIC-RES-0805",
            "Manufacturer": {"Name": "Example Components"},
            "Description": {"ProductDescription": "RES 1.4K OHM 1% 1/8W 0805"},
            "DatasheetUrl": "https://example.com/ds.pdf",
            "ProductUrl": "https://example.com/p",
            "Category": {"Name": "Chip Resistor - Surface Mount"},
            "Parameters": [
                {"ParameterText": "Resistance", "ValueText": "1.4 kOhms"},
                {"ParameterText": "Tolerance", "ValueText": "1%"},
                {"ParameterText": "Power (Watts)", "ValueText": "0.125W"},
                {"ParameterText": "Supplier Device Package", "ValueText": "0805"},
                {"ParameterText": "Mounting Type", "ValueText": "Surface Mount"},
            ],
        }
    ]
}


class _FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _FakeSession:
    def __init__(self, search_handler: Callable[[], _FakeResponse]) -> None:
        self._search_handler = search_handler
        self.calls = 0

    def post(
        self,
        url: str,
        json: Any = None,
        data: Any = None,
        headers: Any = None,
        timeout: float | None = None,
    ) -> _FakeResponse:
        if "/oauth2/token" in url:
            return _FakeResponse(200, {"access_token": "TOK", "expires_in": 600})
        self.calls += 1
        return self._search_handler()


def _provider() -> DigiKeyProvider:
    session = _FakeSession(lambda: _FakeResponse(200, _V4_PAYLOAD))
    return DigiKeyProvider(
        "client-id",
        "client-secret",
        version=DigiKeyApiVersion.V4,
        session=session,  # type: ignore[arg-type]
        max_retries=0,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def test_structured_params_produce_suggestions() -> None:
    rules = AttributeRules(
        rules_by_sachgruppe={
            "Widerstand": ("Wert", "Toleranz", "Leistung", "SmdBauform")
        }
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
    suggested = {s.attribute: s for s in analysis.suggestions}
    # Strukturierte technische Parameter werden auf erlaubte Attribute abgebildet.
    assert suggested["Wert"].suggested_value == "1.4 kOhms"
    assert suggested["Toleranz"].suggested_value == "1%"
    assert suggested["Leistung"].suggested_value == "0.125W"
    # Alle Vorschläge sind Ergänzungen (ERP-Werte sind leer).
    assert all(s.action is SuggestionAction.ERGAENZEN for s in analysis.suggestions)


def test_only_allowed_attributes_are_suggested() -> None:
    # Nur "Wert" ist erlaubt -> Toleranz/Leistung dürfen nicht auftauchen.
    rules = AttributeRules(rules_by_sachgruppe={"Widerstand": ("Wert",)})
    article = Article(
        article_number="ANON-2",
        sachgruppenklasse="Widerstand",
        attributes={"HerstellerNr": "GENERIC-RES-0805"},
    )

    analysis = run_online_analysis([article], rules, _provider())

    attributes = {s.attribute for s in analysis.suggestions}
    assert attributes == {"Wert"}
