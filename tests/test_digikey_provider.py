"""Tests für den DigiKey-Provider (ohne echte API-Aufrufe).

Alle Antworten werden nachgebildet; es findet **kein** echter Netzwerkzugriff
statt. Getestet werden beide API-Versionen (V3/V4), der OAuth-Flow sowie die
robuste Fehlerbehandlung.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import requests

from avor_smart_attribute_manager.analysis.attribute_analyzer import (
    build_default_provider,
)
from avor_smart_attribute_manager.config.settings import (
    DIGIKEY_PROVIDER,
    MOUSER_PROVIDER,
    Settings,
)
from avor_smart_attribute_manager.datasources.digikey import (
    DigiKeyApiVersion,
    DigiKeyProvider,
)
from avor_smart_attribute_manager.datasources.mouser import MouserProvider
from avor_smart_attribute_manager.datasources.provider import (
    MissingApiKeyError,
    ProviderResponseStatus,
)

_TOKEN_URL_FRAGMENT = "/oauth2/token"


class _FakeResponse:
    """Minimaler Ersatz für ``requests.Response``."""

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, ValueError):
            raise self._payload
        return self._payload


def _token_ok() -> _FakeResponse:
    return _FakeResponse(200, {"access_token": "TOK", "expires_in": 600})


class _FakeSession:
    """Beantwortet Token- und Suchanfragen anhand der URL getrennt."""

    def __init__(
        self,
        search_handlers: list[Callable[[], _FakeResponse]],
        token_handler: Callable[[], _FakeResponse] = _token_ok,
    ) -> None:
        self._search_handlers = search_handlers
        self._token_handler = token_handler
        self.search_calls = 0
        self.token_calls = 0
        self.last_headers: dict[str, str] | None = None

    def post(
        self,
        url: str,
        json: Any = None,
        data: Any = None,
        headers: Any = None,
        timeout: float | None = None,
    ) -> _FakeResponse:
        if _TOKEN_URL_FRAGMENT in url:
            self.token_calls += 1
            return self._token_handler()
        self.last_headers = headers
        handler = self._search_handlers[
            min(self.search_calls, len(self._search_handlers) - 1)
        ]
        self.search_calls += 1
        return handler()


def _provider(
    session: _FakeSession,
    *,
    version: DigiKeyApiVersion = DigiKeyApiVersion.V4,
    max_retries: int = 1,
) -> DigiKeyProvider:
    return DigiKeyProvider(
        "client-id",
        "client-secret",
        version=version,
        session=session,  # type: ignore[arg-type]
        max_retries=max_retries,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def _v4_payload() -> dict[str, object]:
    return {
        "Products": [
            {
                "ManufacturerProductNumber": "RC0805FR-071KL",
                "Manufacturer": {"Id": 1, "Name": "Yageo"},
                "Description": {"ProductDescription": "RES 1K OHM 1% 1/8W 0805"},
                "DatasheetUrl": "https://example.com/ds.pdf",
                "ProductUrl": "https://example.com/p",
                "Category": {"Name": "Chip Resistor - Surface Mount"},
                "Parameters": [
                    {"ParameterText": "Resistance", "ValueText": "1 kOhms"},
                    {"ParameterText": "Tolerance", "ValueText": "1%"},
                    {"ParameterText": "Power (Watts)", "ValueText": "0.125W"},
                    {"ParameterText": "Supplier Device Package", "ValueText": "0805"},
                ],
            }
        ]
    }


def _v3_payload() -> dict[str, object]:
    return {
        "Products": [
            {
                "ManufacturerPartNumber": "RC0805FR-071KL",
                "Manufacturer": {"Value": "Yageo"},
                "ProductDescription": "RES 1K OHM 1% 1/8W 0805",
                "PrimaryDatasheet": "https://example.com/ds.pdf",
                "ProductUrl": "https://example.com/p",
                "Category": {"Value": "Chip Resistor - Surface Mount"},
                "Parameters": [
                    {"Parameter": "Resistance", "Value": "1 kOhms"},
                    {"Parameter": "Tolerance", "Value": "1%"},
                    {"Parameter": "Power (Watts)", "Value": "0.125W"},
                    {"Parameter": "Supplier Device Package", "Value": "0805"},
                ],
            }
        ]
    }


def test_missing_client_id_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        DigiKeyProvider("", "secret")


def test_missing_client_secret_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        DigiKeyProvider("client-id", "")


def test_version_from_str_accepts_variants() -> None:
    assert DigiKeyApiVersion.from_str("v3") is DigiKeyApiVersion.V3
    assert DigiKeyApiVersion.from_str("V4") is DigiKeyApiVersion.V4
    assert DigiKeyApiVersion.from_str("4") is DigiKeyApiVersion.V4
    with pytest.raises(ValueError):
        DigiKeyApiVersion.from_str("v5")


def test_name_contains_version() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _v4_payload())])
    assert _provider(session, version=DigiKeyApiVersion.V3).name == "digikey-v3"
    assert _provider(session, version=DigiKeyApiVersion.V4).name == "digikey-v4"


def test_v4_success_parses_products() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _v4_payload())])
    result = _provider(session, version=DigiKeyApiVersion.V4).search_exact(
        "RC0805FR-071KL"
    )

    assert result.status is ProviderResponseStatus.OK
    (product,) = result.products
    assert product.manufacturer_part_number == "RC0805FR-071KL"
    assert product.manufacturer == "Yageo"
    assert product.description == "RES 1K OHM 1% 1/8W 0805"
    assert product.datasheet_url == "https://example.com/ds.pdf"
    assert product.category == "Chip Resistor - Surface Mount"
    assert product.parameters["Resistance"] == "1 kOhms"
    assert product.parameters["Supplier Device Package"] == "0805"
    assert session.token_calls == 1
    assert session.search_calls == 1


def test_v3_success_parses_products() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _v3_payload())])
    result = _provider(session, version=DigiKeyApiVersion.V3).search_exact(
        "RC0805FR-071KL"
    )

    assert result.status is ProviderResponseStatus.OK
    (product,) = result.products
    assert product.manufacturer_part_number == "RC0805FR-071KL"
    assert product.manufacturer == "Yageo"
    assert product.description == "RES 1K OHM 1% 1/8W 0805"
    assert product.datasheet_url == "https://example.com/ds.pdf"
    assert product.category == "Chip Resistor - Surface Mount"
    assert product.parameters["Resistance"] == "1 kOhms"


def test_v3_and_v4_yield_identical_neutral_model() -> None:
    v3 = _provider(
        _FakeSession([lambda: _FakeResponse(200, _v3_payload())]),
        version=DigiKeyApiVersion.V3,
    ).search_exact("RC0805FR-071KL")
    v4 = _provider(
        _FakeSession([lambda: _FakeResponse(200, _v4_payload())]),
        version=DigiKeyApiVersion.V4,
    ).search_exact("RC0805FR-071KL")

    assert v3.products[0].manufacturer_part_number == (
        v4.products[0].manufacturer_part_number
    )
    assert v3.products[0].manufacturer == v4.products[0].manufacturer
    assert dict(v3.products[0].parameters) == dict(v4.products[0].parameters)


def test_auth_headers_are_sent() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _v4_payload())])
    _provider(session).search_exact("RC0805FR-071KL")

    assert session.last_headers is not None
    assert session.last_headers["Authorization"] == "Bearer TOK"
    assert session.last_headers["X-DIGIKEY-Client-Id"] == "client-id"


def test_token_is_reused_across_calls() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _v4_payload())])
    provider = _provider(session)
    provider.search_exact("A")
    provider.search_exact("B")

    assert session.token_calls == 1  # Token wird wiederverwendet
    assert session.search_calls == 2


def test_failed_token_leads_to_api_error() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _v4_payload())],
        token_handler=lambda: _FakeResponse(401, {}),
    )
    result = _provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.search_calls == 0


def test_http_401_invalidates_token_and_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(401, {}),
            lambda: _FakeResponse(200, _v4_payload()),
        ]
    )
    result = _provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.search_calls == 2
    assert session.token_calls == 2  # Token nach 401 neu geholt


def test_rate_limit_http_429() -> None:
    session = _FakeSession([lambda: _FakeResponse(429, {})])
    result = _provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.RATE_LIMITED
    assert session.search_calls == 2


def test_timeout_leads_to_api_error() -> None:
    def _raise() -> _FakeResponse:
        raise requests.Timeout("timeout")

    session = _FakeSession([_raise])
    result = _provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.search_calls == 2


def test_server_error_then_success_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(500, {}),
            lambda: _FakeResponse(200, _v4_payload()),
        ]
    )
    result = _provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.search_calls == 2


def test_client_error_no_retry() -> None:
    session = _FakeSession([lambda: _FakeResponse(400, {})])
    result = _provider(session, max_retries=2).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.search_calls == 1


def test_invalid_json_is_api_error() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, ValueError("bad json"))])
    result = _provider(session).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.API_ERROR


def test_secret_never_leaks_into_error_message() -> None:
    secret = "SUPERSECRET"

    def _raise() -> _FakeResponse:
        raise requests.ConnectionError(f"boom client_secret={secret}")

    session = _FakeSession([_raise])
    provider = DigiKeyProvider(
        "client-id",
        secret,
        session=session,  # type: ignore[arg-type]
        max_retries=0,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )
    result = provider.search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert result.error_message is not None
    assert secret not in result.error_message
    assert "***" in result.error_message


def test_factory_selects_mouser_by_default() -> None:
    provider = build_default_provider(
        Settings(provider=MOUSER_PROVIDER, mouser_api_key="key")
    )
    assert isinstance(provider, MouserProvider)


def test_factory_selects_digikey_with_version() -> None:
    provider = build_default_provider(
        Settings(
            provider=DIGIKEY_PROVIDER,
            digikey_client_id="id",
            digikey_client_secret="secret",
            digikey_api_version=DigiKeyApiVersion.V3,
        )
    )
    assert isinstance(provider, DigiKeyProvider)
    assert provider.name == "digikey-v3"


def test_factory_digikey_without_credentials_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        build_default_provider(Settings(provider=DIGIKEY_PROVIDER))
