"""Tests für den Nexar-Provider (ohne echte API-Aufrufe).

Alle GraphQL- und OAuth-Antworten werden nachgebildet; es findet **kein**
echter Netzwerkzugriff statt. Getestet werden die Authentifizierung (statisches
Token und OAuth2 Client Credentials), die GraphQL-Query, das Parsen
strukturierter Spezifikationen sowie die robuste Fehlerbehandlung inkl.
GraphQL-``errors`` bei HTTP 200.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import requests

from avor_smart_attribute_manager.analysis.attribute_analyzer import (
    build_default_provider,
)
from avor_smart_attribute_manager.config.settings import NEXAR_PROVIDER, Settings
from avor_smart_attribute_manager.datasources.nexar import NexarProvider
from avor_smart_attribute_manager.datasources.provider import (
    MissingApiKeyError,
    ProviderResponseStatus,
)

_TOKEN_URL_FRAGMENT = "connect/token"


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
    """Beantwortet Token- und GraphQL-Anfragen anhand der URL getrennt."""

    def __init__(
        self,
        graphql_handlers: list[Callable[[], _FakeResponse]],
        token_handler: Callable[[], _FakeResponse] = _token_ok,
    ) -> None:
        self._graphql_handlers = graphql_handlers
        self._token_handler = token_handler
        self.graphql_calls = 0
        self.token_calls = 0
        self.last_headers: dict[str, str] | None = None
        self.last_json: Any = None
        self.last_token_data: Any = None

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
            self.last_token_data = data
            return self._token_handler()
        self.last_headers = headers
        self.last_json = json
        handler = self._graphql_handlers[
            min(self.graphql_calls, len(self._graphql_handlers) - 1)
        ]
        self.graphql_calls += 1
        return handler()


def _oauth_provider(
    session: _FakeSession,
    *,
    max_retries: int = 1,
) -> NexarProvider:
    return NexarProvider(
        "client-id",
        "client-secret",
        session=session,  # type: ignore[arg-type]
        max_retries=max_retries,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def _static_provider(
    session: _FakeSession,
    *,
    max_retries: int = 1,
) -> NexarProvider:
    return NexarProvider(
        access_token="STATIC-TOKEN",
        session=session,  # type: ignore[arg-type]
        max_retries=max_retries,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def _success_payload() -> dict[str, object]:
    return {
        "data": {
            "supSearchMpn": {
                "hits": 1,
                "results": [
                    {
                        "part": {
                            "mpn": "RC0805FR-071KL",
                            "manufacturer": {"name": "Yageo"},
                            "shortDescription": "RES 1K OHM 1% 0805",
                            "octopartUrl": "https://octopart.com/p",
                            "category": {"name": "Resistors"},
                            "bestDatasheet": {"url": "https://example.com/ds.pdf"},
                            "specs": [
                                {
                                    "attribute": {
                                        "name": "Resistance",
                                        "shortname": "resistance",
                                        "group": "Electrical",
                                    },
                                    "displayValue": "1 kΩ",
                                    "value": "1000",
                                    "units": "Ohm",
                                    "unitsSymbol": "Ω",
                                },
                                {
                                    "attribute": {
                                        "name": "Tolerance",
                                        "shortname": "tolerance",
                                        "group": "Electrical",
                                    },
                                    "displayValue": "±1%",
                                    "value": "1",
                                    "units": "percent",
                                    "unitsSymbol": "%",
                                },
                            ],
                        }
                    }
                ],
            }
        }
    }


def _graphql_errors(
    message: str, code: str | None = None
) -> dict[str, object]:
    error: dict[str, object] = {"message": message}
    if code is not None:
        error["extensions"] = {"code": code}
    return {"errors": [error]}


# -- Zugangsdaten / Authentifizierung ------------------------------------


def test_missing_credentials_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        NexarProvider()


def test_missing_secret_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        NexarProvider("client-id", "")


def test_static_access_token_skips_oauth() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    result = _static_provider(session).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.token_calls == 0  # kein OAuth bei statischem Token
    assert session.graphql_calls == 1
    assert session.last_headers is not None
    assert session.last_headers["Authorization"] == "Bearer STATIC-TOKEN"


def test_oauth_client_credentials_fetches_token() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    result = _oauth_provider(session).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.token_calls == 1
    assert session.last_token_data is not None
    assert session.last_token_data["grant_type"] == "client_credentials"
    assert session.last_headers is not None
    assert session.last_headers["Authorization"] == "Bearer TOK"


def test_token_is_reused_across_calls() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    provider = _oauth_provider(session)
    provider.search_exact("A")
    provider.search_exact("B")

    assert session.token_calls == 1  # Token wird wiederverwendet
    assert session.graphql_calls == 2


def test_token_endpoint_failure_leads_to_auth_error() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _success_payload())],
        token_handler=lambda: _FakeResponse(401, {}),
    )
    result = _oauth_provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.AUTH_ERROR
    assert session.graphql_calls == 0


def test_token_refresh_after_expiry() -> None:
    clock = {"now": 1000.0}
    session = _FakeSession(
        [lambda: _FakeResponse(200, _success_payload())],
        token_handler=lambda: _FakeResponse(200, {"access_token": "TOK", "expires_in": 60}),
    )
    provider = NexarProvider(
        "client-id",
        "client-secret",
        session=session,  # type: ignore[arg-type]
        max_retries=0,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
        time_source=lambda: clock["now"],
    )
    provider.search_exact("A")
    assert session.token_calls == 1

    # Token läuft ab (60s Laufzeit, 30s Sicherheitsabstand) → Refresh.
    clock["now"] += 100.0
    provider.search_exact("B")
    assert session.token_calls == 2


def test_http_401_invalidates_token_and_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(401, {}),
            lambda: _FakeResponse(200, _success_payload()),
        ]
    )
    result = _oauth_provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.graphql_calls == 2
    assert session.token_calls == 2  # Token nach 401 neu geholt


def test_static_token_401_is_not_retried_endlessly() -> None:
    session = _FakeSession([lambda: _FakeResponse(401, {})])
    result = _static_provider(session, max_retries=3).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.AUTH_ERROR
    # Statisches Token lässt sich nicht erneuern → kein sinnloser Retry.
    assert session.graphql_calls == 1


# -- GraphQL-Query --------------------------------------------------------


def test_query_payload_contains_required_variables() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    _static_provider(session).search_exact("RC0805FR-071KL")

    assert session.last_json is not None
    variables = session.last_json["variables"]
    assert variables["mpn"] == "RC0805FR-071KL"
    assert variables["rankingMethod"] == "DEFAULT"
    assert variables["distributorApiTimeout"] == "20s"
    assert "supSearchMpn" in session.last_json["query"]


# -- Antwort-Parsing ------------------------------------------------------


def test_success_parses_neutral_product() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    result = _static_provider(session).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    (product,) = result.products
    assert product.manufacturer_part_number == "RC0805FR-071KL"
    assert product.manufacturer == "Yageo"
    assert product.description == "RES 1K OHM 1% 0805"
    assert product.category == "Resistors"
    assert product.datasheet_url == "https://example.com/ds.pdf"
    assert product.product_url == "https://octopart.com/p"


def test_success_parses_structured_specs() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    result = _static_provider(session).search_exact("RC0805FR-071KL")

    (product,) = result.products
    specs = {spec.name: spec for spec in product.specs}
    assert specs["resistance"].display_value == "1 kΩ"
    assert specs["resistance"].raw_value == "1000"
    assert specs["resistance"].unit == "Ω"
    assert specs["tolerance"].unit == "%"


def test_missing_specs_yield_empty_tuple() -> None:
    payload = {
        "data": {
            "supSearchMpn": {
                "results": [{"part": {"mpn": "X", "manufacturer": {"name": "M"}}}]
            }
        }
    }
    session = _FakeSession([lambda: _FakeResponse(200, payload)])
    result = _static_provider(session).search_exact("X")

    (product,) = result.products
    assert product.specs == ()
    assert product.parameters == {}


def test_no_results_is_empty_ok() -> None:
    payload = {"data": {"supSearchMpn": {"results": []}}}
    session = _FakeSession([lambda: _FakeResponse(200, payload)])
    result = _static_provider(session).search_exact("X")

    assert result.status is ProviderResponseStatus.OK
    assert result.products == ()


# -- GraphQL-Fehler bei HTTP 200 -----------------------------------------


def test_graphql_generic_error() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors("Something went wrong"))]
    )
    result = _static_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.GRAPHQL_ERROR
    assert result.error_message is not None
    assert "went wrong" in result.error_message


def test_graphql_auth_error_at_http_200() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors("Unauthorized", "UNAUTHORIZED"))]
    )
    result = _oauth_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.AUTH_ERROR


def test_graphql_auth_error_refreshes_oauth_token_and_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(200, _graphql_errors("Token expired", "UNAUTHORIZED")),
            lambda: _FakeResponse(200, _success_payload()),
        ]
    )
    result = _oauth_provider(session, max_retries=1).search_exact("RC0805FR-071KL")

    assert result.status is ProviderResponseStatus.OK
    assert session.graphql_calls == 2
    assert session.token_calls == 2  # Token nach GraphQL-Auth-Fehler neu geholt


def test_graphql_auth_error_with_static_token_is_not_retried() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors("Unauthorized", "UNAUTHORIZED"))]
    )
    result = _static_provider(session, max_retries=3).search_exact("X")

    assert result.status is ProviderResponseStatus.AUTH_ERROR
    # Statisches Token lässt sich nicht erneuern → kein sinnloser Retry.
    assert session.graphql_calls == 1


def test_graphql_part_limit_reached() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors("Monthly part limit exceeded"))]
    )
    result = _static_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.PART_LIMIT_REACHED


def test_graphql_rate_limited() -> None:
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors("Too many requests, throttled"))]
    )
    result = _static_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.RATE_LIMITED


# -- HTTP-Fehler ----------------------------------------------------------


def test_http_429_rate_limited() -> None:
    session = _FakeSession([lambda: _FakeResponse(429, {})])
    result = _static_provider(session, max_retries=1).search_exact("X")

    assert result.status is ProviderResponseStatus.RATE_LIMITED
    assert session.graphql_calls == 2


def test_server_error_then_success_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(503, {}),
            lambda: _FakeResponse(200, _success_payload()),
        ]
    )
    result = _static_provider(session, max_retries=1).search_exact("X")

    assert result.status is ProviderResponseStatus.OK
    assert session.graphql_calls == 2


def test_timeout_leads_to_api_error() -> None:
    def _raise() -> _FakeResponse:
        raise requests.Timeout("timeout")

    session = _FakeSession([_raise])
    result = _static_provider(session, max_retries=1).search_exact("X")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.graphql_calls == 2


def test_invalid_json_is_api_error() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, ValueError("bad json"))])
    result = _static_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.API_ERROR


# -- Sicherheit -----------------------------------------------------------


def test_secret_never_leaks_into_error_message() -> None:
    secret = "SUPERSECRET"

    def _raise() -> _FakeResponse:
        raise requests.ConnectionError(f"boom client_secret={secret}")

    session = _FakeSession([_raise])
    provider = NexarProvider(
        "client-id",
        secret,
        session=session,  # type: ignore[arg-type]
        max_retries=0,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )
    result = provider.search_exact("X")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert result.error_message is not None
    assert secret not in result.error_message
    assert "***" in result.error_message


def test_static_token_never_leaks_into_graphql_error() -> None:
    token = "STATIC-TOKEN"
    session = _FakeSession(
        [lambda: _FakeResponse(200, _graphql_errors(f"failure for token {token}"))]
    )
    result = _static_provider(session, max_retries=0).search_exact("X")

    assert result.status is ProviderResponseStatus.AUTH_ERROR
    assert result.error_message is not None
    assert token not in result.error_message


# -- Name / Version / Factory --------------------------------------------


def test_name_contains_schema_version() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    assert _static_provider(session).name == "nexar-search-mpn-v1"


def test_factory_selects_nexar_with_access_token() -> None:
    provider = build_default_provider(
        Settings(provider=NEXAR_PROVIDER, nexar_access_token="tok")
    )
    assert isinstance(provider, NexarProvider)


def test_factory_selects_nexar_with_client_credentials() -> None:
    provider = build_default_provider(
        Settings(
            provider=NEXAR_PROVIDER,
            nexar_client_id="id",
            nexar_client_secret="secret",
        )
    )
    assert isinstance(provider, NexarProvider)


def test_factory_nexar_without_credentials_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        build_default_provider(Settings(provider=NEXAR_PROVIDER))
