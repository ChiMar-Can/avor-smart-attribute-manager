"""Tests für den Mouser-Provider (ohne echte API-Aufrufe)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
import requests

from avor_smart_attribute_manager.datasources.mouser import MouserProvider
from avor_smart_attribute_manager.datasources.provider import (
    MissingApiKeyError,
    ProviderResponseStatus,
)


class _FakeResponse:
    """Minimaler Ersatz für ``requests.Response``."""

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        if isinstance(self._payload, ValueError):
            raise self._payload
        return self._payload


class _FakeSession:
    """Ruft je Aufruf den nächsten hinterlegten Handler auf."""

    def __init__(self, handlers: list[Callable[[], _FakeResponse]]) -> None:
        self._handlers = handlers
        self.calls = 0

    def post(self, url: str, json: Any = None, timeout: float | None = None) -> _FakeResponse:
        handler = self._handlers[min(self.calls, len(self._handlers) - 1)]
        self.calls += 1
        return handler()


def _provider(session: _FakeSession, *, max_retries: int = 1) -> MouserProvider:
    return MouserProvider(
        "dummy-key",
        session=session,  # type: ignore[arg-type]
        max_retries=max_retries,
        backoff_seconds=0.0,
        sleep=lambda _seconds: None,
    )


def _success_payload() -> dict[str, object]:
    return {
        "Errors": [],
        "SearchResults": {
            "Parts": [
                {
                    "ManufacturerPartNumber": "LM317T",
                    "Manufacturer": "Texas Instruments",
                    "Description": "Adjustable regulator",
                    "Category": "Linear Regulators",
                    "DataSheetUrl": "https://example.com/ds.pdf",
                    "ProductDetailUrl": "https://example.com/p",
                    "ProductAttributes": [
                        {"AttributeName": "Tolerance", "AttributeValue": "1%"},
                    ],
                }
            ]
        },
    }


def test_missing_api_key_raises() -> None:
    with pytest.raises(MissingApiKeyError):
        MouserProvider("")


def test_success_parses_products() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, _success_payload())])
    result = _provider(session).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.OK
    assert len(result.products) == 1
    product = result.products[0]
    assert product.manufacturer_part_number == "LM317T"
    assert product.manufacturer == "Texas Instruments"
    assert product.parameters == {"Tolerance": "1%"}
    assert session.calls == 1


def test_rate_limit_http_429() -> None:
    session = _FakeSession([lambda: _FakeResponse(429, {})])
    result = _provider(session, max_retries=1).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.RATE_LIMITED
    assert session.calls == 2  # Erstversuch + eine Wiederholung


def test_timeout_leads_to_api_error() -> None:
    def _raise() -> _FakeResponse:
        raise requests.Timeout("timeout")

    session = _FakeSession([_raise])
    result = _provider(session, max_retries=1).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.calls == 2


def test_server_error_then_success_retries() -> None:
    session = _FakeSession(
        [
            lambda: _FakeResponse(500, {}),
            lambda: _FakeResponse(200, _success_payload()),
        ]
    )
    result = _provider(session, max_retries=1).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.OK
    assert session.calls == 2


def test_client_error_no_retry() -> None:
    session = _FakeSession([lambda: _FakeResponse(400, {})])
    result = _provider(session, max_retries=2).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.API_ERROR
    assert session.calls == 1


def test_invalid_json_is_api_error() -> None:
    session = _FakeSession([lambda: _FakeResponse(200, ValueError("bad json"))])
    result = _provider(session).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.API_ERROR


def test_errors_field_rate_limit() -> None:
    payload = {"Errors": [{"Message": "Too many requests"}]}
    session = _FakeSession([lambda: _FakeResponse(200, payload)])
    result = _provider(session).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.RATE_LIMITED


def test_errors_field_generic_api_error() -> None:
    payload = {"Errors": [{"Message": "Invalid API key"}]}
    session = _FakeSession([lambda: _FakeResponse(200, payload)])
    result = _provider(session).search_exact("LM317T")

    assert result.status is ProviderResponseStatus.API_ERROR
