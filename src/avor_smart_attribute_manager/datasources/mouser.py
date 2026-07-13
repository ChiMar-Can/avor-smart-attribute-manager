"""Konkreter Provider für die offizielle Mouser Search API.

Es wird ausschliesslich die offizielle API verwendet – **kein** Web-Scraping.
Der API-Schlüssel wird niemals im Repository gespeichert, sondern über eine
Umgebungsvariable (:data:`API_KEY_ENV_VAR`) bereitgestellt.

Die Antwort der Mouser-API wird direkt in das neutrale Datenmodell
(:class:`ProviderSearchResult`) überführt; die Analyse hängt dadurch nicht von
Mouser-spezifischen Strukturen ab.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    MissingApiKeyError,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)

#: Name der Umgebungsvariable, die den Mouser-API-Schlüssel enthält.
API_KEY_ENV_VAR = "MOUSER_API_KEY"

#: Providername (kleingeschrieben, stabil für Cache-Trennung).
PROVIDER_NAME = "mouser"

#: Basis-URL der Mouser Search API (Keyword-Suche).
DEFAULT_BASE_URL = "https://api.mouser.com/api/v1/search/keyword"

#: Standardwerte für Timeout, Wiederholungen und Backoff.
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_SECONDS = 0.5

#: Maximale Anzahl abgefragter Datensätze pro Suche.
_MAX_RECORDS = 20


def _optional_str(value: object) -> str | None:
    """Liefert einen bereinigten String oder ``None`` bei leeren Werten."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


class MouserProvider(ComponentDataProvider):
    """Datenquelle auf Basis der offiziellen Mouser Search API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialisiert den Provider.

        Args:
            api_key: Mouser-API-Schlüssel (nicht leer).
            base_url: Endpunkt der Keyword-Suche.
            timeout: Timeout je Anfrage in Sekunden.
            max_retries: Zusätzliche Wiederholungen bei temporären Fehlern.
            backoff_seconds: Basiswert für exponentiellen Backoff.
            session: Optionale ``requests``-Session (v. a. für Tests).
            sleep: Sleep-Funktion (injizierbar für Tests).

        Raises:
            MissingApiKeyError: Wenn kein API-Schlüssel übergeben wurde.
        """
        if not api_key or not api_key.strip():
            raise MissingApiKeyError(
                "Kein Mouser-API-Schlüssel gesetzt. Bitte die Umgebungsvariable "
                f"'{API_KEY_ENV_VAR}' setzen (siehe README/.env.example)."
            )
        self._api_key = api_key.strip()
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._session = session if session is not None else requests.Session()
        self._sleep = sleep

    @property
    def name(self) -> str:
        """Providername (``"mouser"``)."""
        return PROVIDER_NAME

    def _parse_part(self, part: dict[str, object]) -> ProviderProduct:
        """Überführt einen Mouser-Part in das neutrale Produktmodell."""
        parameters: dict[str, str] = {}
        raw_attributes = part.get("ProductAttributes")
        if isinstance(raw_attributes, list):
            for attribute in raw_attributes:
                if not isinstance(attribute, dict):
                    continue
                name = _optional_str(attribute.get("AttributeName"))
                value = _optional_str(attribute.get("AttributeValue"))
                if name is not None and value is not None:
                    parameters[name] = value

        return ProviderProduct(
            manufacturer_part_number=_optional_str(
                part.get("ManufacturerPartNumber")
            ),
            manufacturer=_optional_str(part.get("Manufacturer")),
            description=_optional_str(part.get("Description")),
            category=_optional_str(part.get("Category")),
            datasheet_url=_optional_str(part.get("DataSheetUrl")),
            product_url=_optional_str(part.get("ProductDetailUrl")),
            parameters=parameters,
        )

    def _parse_success(self, data: object) -> ProviderSearchResult:
        """Wertet eine erfolgreiche HTTP-Antwort (Status 200) aus."""
        if not isinstance(data, dict):
            return ProviderSearchResult(
                provider=self.name,
                status=ProviderResponseStatus.API_ERROR,
                error_message="Unerwartetes Antwortformat der Mouser-API.",
            )

        errors = data.get("Errors")
        if isinstance(errors, list) and errors:
            messages = [
                message
                for error in errors
                if isinstance(error, dict)
                and (message := _optional_str(error.get("Message"))) is not None
            ]
            joined = "; ".join(messages) or "Unbekannter API-Fehler."
            status = (
                ProviderResponseStatus.RATE_LIMITED
                if "too many" in joined.lower() or "rate" in joined.lower()
                else ProviderResponseStatus.API_ERROR
            )
            return ProviderSearchResult(
                provider=self.name, status=status, error_message=joined
            )

        search_results = data.get("SearchResults")
        parts = search_results.get("Parts") if isinstance(search_results, dict) else None
        products = (
            tuple(
                self._parse_part(part)
                for part in parts
                if isinstance(part, dict)
            )
            if isinstance(parts, list)
            else ()
        )
        return ProviderSearchResult(
            provider=self.name,
            status=ProviderResponseStatus.OK,
            products=products,
        )

    def search_exact(
        self,
        manufacturer_part_number: str,
        manufacturer: str | None = None,
    ) -> ProviderSearchResult:
        """Sucht bei Mouser nach einer Herstellerteilenummer.

        Args:
            manufacturer_part_number: Bereits technisch bereinigte
                Herstellerteilenummer.
            manufacturer: Optionaler Hersteller (nicht Teil der Anfrage, wird
                nachgelagert zur Plausibilitätsprüfung genutzt).

        Returns:
            Ein :class:`ProviderSearchResult`. Technische Fehler führen nicht zu
            einer Ausnahme, sondern zu einem entsprechenden Status.
        """
        url = f"{self._base_url}?apiKey={self._api_key}"
        payload: dict[str, Any] = {
            "SearchByKeywordRequest": {
                "keyword": manufacturer_part_number,
                "records": _MAX_RECORDS,
                "startingRecord": 0,
            }
        }

        last_error = "Anfrage fehlgeschlagen."
        rate_limited = False
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.post(
                    url, json=payload, timeout=self._timeout
                )
            except requests.Timeout as error:
                last_error = f"Zeitüberschreitung bei der Anfrage: {error}"
            except requests.RequestException as error:
                last_error = f"Verbindungsfehler bei der Anfrage: {error}"
            else:
                if response.status_code == 429:
                    rate_limited = True
                    last_error = "Rate-Limit erreicht (HTTP 429)."
                elif response.status_code >= 500:
                    last_error = f"Serverfehler der Mouser-API (HTTP {response.status_code})."
                elif response.status_code != 200:
                    return ProviderSearchResult(
                        provider=self.name,
                        status=ProviderResponseStatus.API_ERROR,
                        error_message=(
                            f"Mouser-API antwortete mit HTTP {response.status_code}."
                        ),
                    )
                else:
                    try:
                        data = response.json()
                    except ValueError:
                        return ProviderSearchResult(
                            provider=self.name,
                            status=ProviderResponseStatus.API_ERROR,
                            error_message="Antwort der Mouser-API ist kein gültiges JSON.",
                        )
                    return self._parse_success(data)

            if attempt < self._max_retries:
                self._sleep(self._backoff_seconds * (2**attempt))

        status = (
            ProviderResponseStatus.RATE_LIMITED
            if rate_limited
            else ProviderResponseStatus.API_ERROR
        )
        return ProviderSearchResult(
            provider=self.name, status=status, error_message=last_error
        )
