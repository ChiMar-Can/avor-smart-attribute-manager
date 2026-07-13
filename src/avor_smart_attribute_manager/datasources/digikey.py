"""Konkreter Provider für die offizielle DigiKey Product Information API.

Unterstützt **beide** aktuell relevanten API-Versionen:

* **Product Information V3** (Endpunkt ``/Search/v3/Products/Keyword``)
* **Product Information V4** (Endpunkt ``/products/v4/search/keyword``)

Die verwendete Version ist konfigurierbar (:data:`API_VERSION_ENV_VAR`) und
**nicht** in der Fachlogik fest verdrahtet. Beide Versionen werden in dasselbe
neutrale Datenmodell (:class:`ProviderSearchResult`) überführt; die Analyse
hängt dadurch weder von DigiKey- noch von versionsspezifischen Strukturen ab.

Es wird ausschliesslich die offizielle API verwendet – **kein** Web-Scraping.
Die Zugangsdaten (Client-ID/Client-Secret, OAuth-Token) werden niemals im
Repository gespeichert; sie werden über Umgebungsvariablen bereitgestellt und
aus allen Fehlermeldungen redigiert (sie könnten sonst in die Ergebnis-Excel
gelangen).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum
from typing import Any

import requests

from avor_smart_attribute_manager.datasources.provider import (
    ComponentDataProvider,
    MissingApiKeyError,
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)

#: Umgebungsvariablen für die DigiKey-Zugangsdaten und -Konfiguration.
CLIENT_ID_ENV_VAR = "DIGIKEY_CLIENT_ID"
CLIENT_SECRET_ENV_VAR = "DIGIKEY_CLIENT_SECRET"
API_VERSION_ENV_VAR = "DIGIKEY_API_VERSION"
BASE_URL_ENV_VAR = "DIGIKEY_BASE_URL"

#: Providername-Präfix (die konkrete ``name``-Eigenschaft enthält die Version,
#: damit der lokale Cache V3- und V4-Ergebnisse sauber trennt).
PROVIDER_PREFIX = "digikey"

#: Produktions-Basis-URL der DigiKey-API (Sandbox per Konfiguration möglich).
DEFAULT_BASE_URL = "https://api.digikey.com"

#: Standardwerte für Timeout, Wiederholungen und Backoff.
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_SECONDS = 0.5

#: Standard-Locale-Header (beeinflusst Währung/Sprache, nicht die Parameternamen).
DEFAULT_LOCALE_SITE = "CH"
DEFAULT_LOCALE_LANGUAGE = "en"
DEFAULT_LOCALE_CURRENCY = "CHF"

#: Maximale Anzahl abgefragter Datensätze pro Suche.
_MAX_RECORDS = 20

#: Sicherheitsabstand (Sekunden), bevor ein OAuth-Token als abgelaufen gilt.
_TOKEN_EXPIRY_MARGIN_SECONDS = 30.0


class DigiKeyApiVersion(Enum):
    """Unterstützte DigiKey-API-Versionen.

    Attributes:
        V3: Product Information V3.
        V4: Product Information V4.
    """

    V3 = "v3"
    V4 = "v4"

    @classmethod
    def from_str(cls, value: str) -> DigiKeyApiVersion:
        """Wandelt einen Konfigurationswert (z. B. ``"v4"``) in die Enum um.

        Args:
            value: Konfigurierter Versionswert (case-insensitive, mit/ohne ``v``).

        Returns:
            Die passende :class:`DigiKeyApiVersion`.

        Raises:
            ValueError: Wenn der Wert keiner unterstützten Version entspricht.
        """
        normalized = value.strip().lower().lstrip("v")
        for version in cls:
            if version.value == f"v{normalized}":
                return version
        supported = ", ".join(sorted(v.value for v in cls))
        raise ValueError(
            f"Unbekannte DigiKey-API-Version '{value}'. Unterstützt: {supported}."
        )


def _optional_str(value: object) -> str | None:
    """Liefert einen bereinigten String oder ``None`` bei leeren Werten."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _nested_str(container: object, *keys: str) -> str | None:
    """Liest einen verschachtelten String (``container[keys[0]][keys[1]]...``)."""
    current: object = container
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return _optional_str(current)


class DigiKeyProvider(ComponentDataProvider):
    """Datenquelle auf Basis der offiziellen DigiKey Product Information API.

    Der Provider kapselt den OAuth2-Client-Credentials-Flow und die
    versionsabhängige Antwortauswertung vollständig. Nach aussen verhält er sich
    identisch zu jedem anderen :class:`ComponentDataProvider`.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        version: DigiKeyApiVersion = DigiKeyApiVersion.V4,
        base_url: str = DEFAULT_BASE_URL,
        locale_site: str = DEFAULT_LOCALE_SITE,
        locale_language: str = DEFAULT_LOCALE_LANGUAGE,
        locale_currency: str = DEFAULT_LOCALE_CURRENCY,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialisiert den Provider.

        Args:
            client_id: DigiKey-Client-ID (nicht leer).
            client_secret: DigiKey-Client-Secret (nicht leer).
            version: Zu verwendende API-Version (Standard: V4).
            base_url: Basis-URL der API (Produktion oder Sandbox).
            locale_site: Locale-Land-Header (z. B. ``"CH"``).
            locale_language: Locale-Sprache-Header (z. B. ``"en"``).
            locale_currency: Locale-Währung-Header (z. B. ``"CHF"``).
            timeout: Timeout je Anfrage in Sekunden.
            max_retries: Zusätzliche Wiederholungen bei temporären Fehlern.
            backoff_seconds: Basiswert für exponentiellen Backoff.
            session: Optionale ``requests``-Session (v. a. für Tests).
            sleep: Sleep-Funktion (injizierbar für Tests).
            time_source: Monotone Zeitquelle für die Token-Gültigkeit (Tests).

        Raises:
            MissingApiKeyError: Wenn Client-ID oder Client-Secret fehlen.
        """
        if not client_id or not client_id.strip():
            raise MissingApiKeyError(
                "Keine DigiKey-Client-ID gesetzt. Bitte die Umgebungsvariable "
                f"'{CLIENT_ID_ENV_VAR}' setzen (siehe README/.env.example)."
            )
        if not client_secret or not client_secret.strip():
            raise MissingApiKeyError(
                "Kein DigiKey-Client-Secret gesetzt. Bitte die Umgebungsvariable "
                f"'{CLIENT_SECRET_ENV_VAR}' setzen (siehe README/.env.example)."
            )
        self._client_id = client_id.strip()
        self._client_secret = client_secret.strip()
        self._version = version
        self._base_url = base_url.rstrip("/")
        self._locale_site = locale_site
        self._locale_language = locale_language
        self._locale_currency = locale_currency
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._session = session if session is not None else requests.Session()
        self._sleep = sleep
        self._time_source = time_source
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    @property
    def name(self) -> str:
        """Providername inkl. Version (z. B. ``"digikey-v4"``).

        Die Version ist Teil des Namens, damit der lokale Cache V3- und
        V4-Ergebnisse getrennt hält.
        """
        return f"{PROVIDER_PREFIX}-{self._version.value}"

    @property
    def version(self) -> DigiKeyApiVersion:
        """Die konfigurierte API-Version."""
        return self._version

    def _redact(self, text: str) -> str:
        """Entfernt Zugangsdaten (Secret/Token) aus einer Fehlermeldung.

        Fehlermeldungen können in die Ergebnis-Excel (Spalte ``Meldung``)
        gelangen; Zugangsdaten dürfen dort **niemals** erscheinen.

        Args:
            text: Ursprüngliche Fehlermeldung.

        Returns:
            Die Meldung mit ersetzten Zugangsdaten.
        """
        redacted = text.replace(self._client_secret, "***")
        if self._access_token:
            redacted = redacted.replace(self._access_token, "***")
        return redacted

    # -- OAuth2 (Client Credentials) ------------------------------------

    def _ensure_token(self) -> str | None:
        """Stellt ein gültiges OAuth-Token bereit (holt bei Bedarf ein neues).

        Returns:
            Das gültige Bearer-Token oder ``None``, falls die Token-Abfrage
            technisch fehlschlug. Im Fehlerfall bleibt kein Token gecacht.
        """
        now = self._time_source()
        if self._access_token is not None and now < self._token_expires_at:
            return self._access_token

        token_url = f"{self._base_url}/v1/oauth2/token"
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "client_credentials",
        }
        try:
            response = self._session.post(
                token_url, data=data, timeout=self._timeout
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None

        token = _optional_str(payload.get("access_token"))
        if token is None:
            return None
        expires_in = payload.get("expires_in")
        lifetime = float(expires_in) if isinstance(expires_in, (int, float)) else 300.0
        self._access_token = token
        self._token_expires_at = (
            self._time_source() + max(lifetime - _TOKEN_EXPIRY_MARGIN_SECONDS, 0.0)
        )
        return token

    def _invalidate_token(self) -> None:
        """Verwirft ein (möglicherweise abgelaufenes) Token."""
        self._access_token = None
        self._token_expires_at = 0.0

    def _error_detail(self, response: requests.Response) -> str:
        """Liest eine kurze, redigierte Fehlerbeschreibung aus der Antwort.

        DigiKey liefert bei Fehlern eine erklärende Meldung (V4: ``detail``,
        V3: ``ErrorMessage``). Diese wird – ohne Zugangsdaten – an die Statusmeldung
        angehängt, damit z. B. eine fehlende API-Subscription direkt erkennbar ist.

        Args:
            response: Die HTTP-Fehlerantwort.

        Returns:
            Eine mit führendem Leerzeichen versehene, redigierte Detailmeldung
            oder ein leerer String.
        """
        try:
            body = response.json()
        except ValueError:
            return ""
        if isinstance(body, dict):
            detail = _optional_str(body.get("detail")) or _optional_str(
                body.get("ErrorMessage")
            )
            if detail is not None:
                return f" {self._redact(detail)}"
        return ""

    # -- Versionsabhängige Endpunkte/Parser -----------------------------

    def _search_endpoint(self) -> str:
        """Liefert den versionsabhängigen Keyword-Suchendpunkt."""
        if self._version is DigiKeyApiVersion.V3:
            return f"{self._base_url}/Search/v3/Products/Keyword"
        return f"{self._base_url}/products/v4/search/keyword"

    def _search_payload(self, keyword: str) -> dict[str, Any]:
        """Erzeugt den versionsabhängigen Anfrage-Body."""
        if self._version is DigiKeyApiVersion.V3:
            return {"Keywords": keyword, "RecordCount": _MAX_RECORDS}
        return {"Keywords": keyword, "Limit": _MAX_RECORDS}

    def _headers(self, token: str) -> dict[str, str]:
        """Erzeugt die Anfrage-Header inkl. Authentifizierung und Locale."""
        return {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": self._client_id,
            "X-DIGIKEY-Locale-Site": self._locale_site,
            "X-DIGIKEY-Locale-Language": self._locale_language,
            "X-DIGIKEY-Locale-Currency": self._locale_currency,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _parse_v3_product(self, product: dict[str, object]) -> ProviderProduct:
        """Überführt einen V3-Produktdatensatz in das neutrale Modell."""
        parameters: dict[str, str] = {}
        raw_parameters = product.get("Parameters")
        if isinstance(raw_parameters, list):
            for parameter in raw_parameters:
                if not isinstance(parameter, dict):
                    continue
                name = _optional_str(parameter.get("Parameter"))
                value = _optional_str(parameter.get("Value"))
                if name is not None and value is not None:
                    parameters.setdefault(name, value)

        return ProviderProduct(
            manufacturer_part_number=_optional_str(
                product.get("ManufacturerPartNumber")
            ),
            manufacturer=_nested_str(product.get("Manufacturer"), "Value"),
            description=_optional_str(product.get("ProductDescription")),
            category=_nested_str(product.get("Category"), "Value"),
            datasheet_url=_optional_str(product.get("PrimaryDatasheet")),
            product_url=_optional_str(product.get("ProductUrl")),
            parameters=parameters,
        )

    def _parse_v4_product(self, product: dict[str, object]) -> ProviderProduct:
        """Überführt einen V4-Produktdatensatz in das neutrale Modell."""
        parameters: dict[str, str] = {}
        raw_parameters = product.get("Parameters")
        if isinstance(raw_parameters, list):
            for parameter in raw_parameters:
                if not isinstance(parameter, dict):
                    continue
                name = _optional_str(parameter.get("ParameterText"))
                value = _optional_str(parameter.get("ValueText"))
                if name is not None and value is not None:
                    parameters.setdefault(name, value)

        return ProviderProduct(
            manufacturer_part_number=_optional_str(
                product.get("ManufacturerProductNumber")
            ),
            manufacturer=_nested_str(product.get("Manufacturer"), "Name"),
            description=_nested_str(product.get("Description"), "ProductDescription"),
            category=_nested_str(product.get("Category"), "Name"),
            datasheet_url=_optional_str(product.get("DatasheetUrl")),
            product_url=_optional_str(product.get("ProductUrl")),
            parameters=parameters,
        )

    def _parse_success(self, data: object) -> ProviderSearchResult:
        """Wertet eine erfolgreiche HTTP-Antwort (Status 200) aus."""
        if not isinstance(data, dict):
            return ProviderSearchResult(
                provider=self.name,
                status=ProviderResponseStatus.API_ERROR,
                error_message="Unerwartetes Antwortformat der DigiKey-API.",
            )

        raw_products = data.get("Products")
        parse = (
            self._parse_v3_product
            if self._version is DigiKeyApiVersion.V3
            else self._parse_v4_product
        )
        products = (
            tuple(
                parse(product)
                for product in raw_products
                if isinstance(product, dict)
            )
            if isinstance(raw_products, list)
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
        """Sucht bei DigiKey nach einer Herstellerteilenummer.

        Args:
            manufacturer_part_number: Bereits technisch bereinigte
                Herstellerteilenummer.
            manufacturer: Optionaler Hersteller (nicht Teil der Anfrage, wird
                nachgelagert zur Plausibilitätsprüfung genutzt).

        Returns:
            Ein :class:`ProviderSearchResult`. Technische Fehler führen nicht zu
            einer Ausnahme, sondern zu einem entsprechenden Status.
        """
        url = self._search_endpoint()
        payload = self._search_payload(manufacturer_part_number)

        last_error = "Anfrage fehlgeschlagen."
        rate_limited = False
        for attempt in range(self._max_retries + 1):
            token = self._ensure_token()
            if token is None:
                last_error = "OAuth-Authentifizierung bei DigiKey fehlgeschlagen."
            else:
                try:
                    response = self._session.post(
                        url,
                        json=payload,
                        headers=self._headers(token),
                        timeout=self._timeout,
                    )
                except requests.Timeout as error:
                    last_error = self._redact(
                        f"Zeitüberschreitung bei der Anfrage: {error}"
                    )
                except requests.RequestException as error:
                    last_error = self._redact(
                        f"Verbindungsfehler bei der Anfrage: {error}"
                    )
                else:
                    if response.status_code == 401:
                        # Token evtl. abgelaufen: verwerfen und erneut versuchen.
                        detail = self._error_detail(response)
                        self._invalidate_token()
                        last_error = (
                            "DigiKey-API: Authentifizierung abgelehnt (HTTP 401)."
                            f"{detail}"
                        )
                    elif response.status_code == 429:
                        rate_limited = True
                        last_error = "Rate-Limit erreicht (HTTP 429)."
                    elif response.status_code >= 500:
                        last_error = (
                            "Serverfehler der DigiKey-API "
                            f"(HTTP {response.status_code})."
                        )
                    elif response.status_code != 200:
                        return ProviderSearchResult(
                            provider=self.name,
                            status=ProviderResponseStatus.API_ERROR,
                            error_message=(
                                f"DigiKey-API antwortete mit HTTP "
                                f"{response.status_code}.{self._error_detail(response)}"
                            ),
                        )
                    else:
                        try:
                            data = response.json()
                        except ValueError:
                            return ProviderSearchResult(
                                provider=self.name,
                                status=ProviderResponseStatus.API_ERROR,
                                error_message=(
                                    "Antwort der DigiKey-API ist kein gültiges JSON."
                                ),
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
