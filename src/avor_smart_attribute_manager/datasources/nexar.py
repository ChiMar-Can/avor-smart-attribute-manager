"""Konkreter Provider für die offizielle Nexar (Octopart) GraphQL Supply API.

Der Provider fragt strukturierte Produktdaten über die offizielle GraphQL-API ab
(``supSearchMpn``) – **kein** Web-Scraping. Alle GraphQL-spezifischen Strukturen
werden ausschliesslich hier behandelt und in das neutrale Datenmodell
(:class:`ProviderSearchResult`) überführt; die Fachlogik kennt weder GraphQL noch
Nexar-Strukturen.

Authentifizierung (Priorität):

1. Statisches Zugriffstoken (:data:`ACCESS_TOKEN_ENV_VAR`), falls gesetzt.
2. Sonst OAuth2 Client Credentials (:data:`CLIENT_ID_ENV_VAR` /
   :data:`CLIENT_SECRET_ENV_VAR`).
3. Andernfalls ein klarer Konfigurationsfehler (:class:`MissingApiKeyError`).

Sicherheit: Zugangsdaten und Tokens werden ausschliesslich im Speicher gehalten,
niemals im Repository, Cache, Log oder in der Ergebnis-Excel gespeichert und aus
allen Fehlermeldungen redigiert.
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
    ProviderSpec,
)

#: Umgebungsvariablen für die Nexar-Zugangsdaten.
CLIENT_ID_ENV_VAR = "NEXAR_CLIENT_ID"
CLIENT_SECRET_ENV_VAR = "NEXAR_CLIENT_SECRET"
ACCESS_TOKEN_ENV_VAR = "NEXAR_ACCESS_TOKEN"

#: Providername-Präfix.
PROVIDER_PREFIX = "nexar"

#: Version der verwendeten GraphQL-Query/-Auswertung. Teil des Providernamens,
#: damit der lokale Cache bei Schema-/Query-Änderungen sauber getrennt wird.
QUERY_SCHEMA_VERSION = "search-mpn-v1"

#: Offizielle Endpunkte (zentral geführt).
DEFAULT_TOKEN_URL = "https://identity.nexar.com/connect/token"
DEFAULT_GRAPHQL_URL = "https://api.nexar.com/graphql"

#: OAuth-Scope der Nexar Supply-Domain.
DEFAULT_SCOPE = "supply.domain"

#: Standard-Locale (beeinflusst nur Preise, nicht die technischen Spezifikationen).
DEFAULT_COUNTRY = "CH"
DEFAULT_CURRENCY = "CHF"

#: Pflicht-Ranking der ``supSearchMpn``-Abfrage (Enum ``SupSearchRankingMethod``).
#: Gültige Werte laut Schema: ``DEFAULT``, ``SUPPLY``, ``DESIGN``.
DEFAULT_RANKING_METHOD = "DEFAULT"

#: Pflicht-Timeout für optionale Distributor-API-Aufrufe (String, Schema-Pflicht).
#: Distributor-Pricing wird bewusst nicht genutzt (``distributorApi: false``).
DEFAULT_DISTRIBUTOR_API_TIMEOUT = "20s"

#: Standardwerte für Timeout, Wiederholungen und Backoff.
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_SECONDS = 0.5

#: Maximale Anzahl abgefragter Datensätze pro Suche.
_MAX_RECORDS = 10

#: Sicherheitsabstand (Sekunden), bevor ein OAuth-Token als abgelaufen gilt.
_TOKEN_EXPIRY_MARGIN_SECONDS = 30.0

#: GraphQL-Query für die exakte MPN-Suche (nur benötigte Felder).
#: ``rankingMethod`` und ``distributorApiTimeout`` sind laut Schema Pflicht.
_MPN_SEARCH_QUERY = """
query AvorNexarMpnSearch(
  $mpn: String!
  $limit: Int!
  $country: String!
  $currency: String!
  $rankingMethod: SupSearchRankingMethod!
  $distributorApiTimeout: String!
) {
  supSearchMpn(
    q: $mpn
    limit: $limit
    country: $country
    currency: $currency
    rankingMethod: $rankingMethod
    distributorApi: false
    distributorApiTimeout: $distributorApiTimeout
  ) {
    hits
    results {
      part {
        mpn
        manufacturer { name }
        shortDescription
        octopartUrl
        category { name }
        bestDatasheet { url }
        specs {
          attribute { name shortname group }
          displayValue
          value
          units
          unitsSymbol
        }
      }
    }
  }
}
""".strip()


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


def _classify_graphql_errors(errors: list[object]) -> tuple[ProviderResponseStatus, str]:
    """Klassifiziert GraphQL-``errors`` in einen Provider-Status + Meldung.

    GraphQL liefert Fehler auch bei HTTP 200. Anhand von ``extensions.code`` und
    der Meldung werden Authentifizierungs-, Rate-Limit-, Teilelimit- und
    allgemeine GraphQL-Fehler unterschieden.

    Args:
        errors: Die ``errors``-Liste der GraphQL-Antwort.

    Returns:
        Ein Tupel aus Provider-Status und zusammengefasster Meldung.
    """
    messages: list[str] = []
    codes: list[str] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        message = _optional_str(error.get("message"))
        if message is not None:
            messages.append(message)
        extensions = error.get("extensions")
        if isinstance(extensions, dict):
            code = _optional_str(extensions.get("code"))
            if code is not None:
                codes.append(code)

    joined = "; ".join(messages) or "Unbekannter GraphQL-Fehler."
    haystack = f"{joined} {' '.join(codes)}".lower()

    if any(
        marker in haystack
        for marker in ("auth", "token", "unauthorized", "forbidden", "permission")
    ):
        return ProviderResponseStatus.AUTH_ERROR, joined
    if any(
        marker in haystack
        for marker in ("part limit", "partlimit", "quota", "exceeded", "limit reached")
    ):
        return ProviderResponseStatus.PART_LIMIT_REACHED, joined
    if any(
        marker in haystack
        for marker in ("rate", "throttl", "too many")
    ):
        return ProviderResponseStatus.RATE_LIMITED, joined
    return ProviderResponseStatus.GRAPHQL_ERROR, joined


class NexarProvider(ComponentDataProvider):
    """Datenquelle auf Basis der offiziellen Nexar (Octopart) GraphQL Supply API.

    Der Provider kapselt Authentifizierung (statisches Token oder OAuth2 Client
    Credentials), die GraphQL-Abfrage sowie die GraphQL-Fehlerbehandlung
    vollständig. Nach aussen verhält er sich identisch zu jedem anderen
    :class:`ComponentDataProvider`.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        *,
        access_token: str | None = None,
        token_url: str = DEFAULT_TOKEN_URL,
        graphql_url: str = DEFAULT_GRAPHQL_URL,
        scope: str = DEFAULT_SCOPE,
        country: str = DEFAULT_COUNTRY,
        currency: str = DEFAULT_CURRENCY,
        ranking_method: str = DEFAULT_RANKING_METHOD,
        distributor_api_timeout: str = DEFAULT_DISTRIBUTOR_API_TIMEOUT,
        limit: int = _MAX_RECORDS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF_SECONDS,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialisiert den Provider.

        Args:
            client_id: Nexar-Client-ID (für OAuth2 Client Credentials).
            client_secret: Nexar-Client-Secret (für OAuth2 Client Credentials).
            access_token: Optionales statisches Zugriffstoken (hat Vorrang vor
                OAuth2).
            token_url: OAuth-Token-Endpunkt.
            graphql_url: GraphQL-Endpunkt.
            scope: OAuth-Scope.
            country: Locale-Land (nur Preisbezug, nicht die Spezifikationen).
            currency: Locale-Währung (nur Preisbezug).
            ranking_method: Pflicht-Ranking der Suche (``DEFAULT``/``SUPPLY``/
                ``DESIGN``); beeinflusst nur die Trefferreihenfolge.
            distributor_api_timeout: Pflicht-Timeout-String der Distributor-API
                (Distributor-Pricing wird nicht genutzt).
            limit: Maximale Anzahl abgefragter Datensätze pro Suche.
            timeout: Timeout je Anfrage in Sekunden.
            max_retries: Zusätzliche Wiederholungen bei temporären Fehlern.
            backoff_seconds: Basiswert für exponentiellen Backoff.
            session: Optionale ``requests``-Session (v. a. für Tests).
            sleep: Sleep-Funktion (injizierbar für Tests).
            time_source: Monotone Zeitquelle für die Token-Gültigkeit (Tests).

        Raises:
            MissingApiKeyError: Wenn weder ein Zugriffstoken noch ein
                vollständiges Client-Credentials-Paar bereitgestellt wurde.
        """
        static_token = (access_token or "").strip() or None
        cleaned_id = (client_id or "").strip() or None
        cleaned_secret = (client_secret or "").strip() or None

        if static_token is None and (cleaned_id is None or cleaned_secret is None):
            raise MissingApiKeyError(
                "Keine Nexar-Zugangsdaten gesetzt. Bitte entweder "
                f"'{ACCESS_TOKEN_ENV_VAR}' oder '{CLIENT_ID_ENV_VAR}' und "
                f"'{CLIENT_SECRET_ENV_VAR}' setzen (siehe README/.env.example)."
            )

        self._client_id = cleaned_id
        self._client_secret = cleaned_secret
        self._static_token = static_token
        self._token_url = token_url
        self._graphql_url = graphql_url
        self._scope = scope
        self._country = country
        self._currency = currency
        self._ranking_method = ranking_method
        self._distributor_api_timeout = distributor_api_timeout
        self._limit = limit
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._session = session if session is not None else requests.Session()
        self._sleep = sleep
        self._time_source = time_source
        self._access_token: str | None = static_token
        self._token_expires_at = float("inf") if static_token is not None else 0.0

    @property
    def name(self) -> str:
        """Providername inkl. Query-/Schema-Version (z. B. ``"nexar-search-mpn-v1"``).

        Die Version ist Teil des Namens, damit der lokale Cache bei einer
        Query-/Schema-Änderung nicht versehentlich veraltete Ergebnisse
        wiederverwendet.
        """
        return f"{PROVIDER_PREFIX}-{QUERY_SCHEMA_VERSION}"

    def _redact(self, text: str) -> str:
        """Entfernt Zugangsdaten (Secret/Token) aus einer Meldung."""
        redacted = text
        for secret in (self._client_secret, self._access_token, self._static_token):
            if secret:
                redacted = redacted.replace(secret, "***")
        return redacted

    # -- Authentifizierung ----------------------------------------------

    def _ensure_token(self) -> str | None:
        """Stellt ein gültiges Token bereit (statisch oder via OAuth2).

        Returns:
            Das gültige Bearer-Token oder ``None``, falls die Token-Abfrage
            technisch fehlschlug. Im Fehlerfall bleibt kein Token gecacht.
        """
        if self._static_token is not None:
            return self._static_token

        now = self._time_source()
        if self._access_token is not None and now < self._token_expires_at:
            return self._access_token

        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": self._scope,
        }
        try:
            response = self._session.post(
                self._token_url, data=data, timeout=self._timeout
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
        self._token_expires_at = self._time_source() + max(
            lifetime - _TOKEN_EXPIRY_MARGIN_SECONDS, 0.0
        )
        return token

    def _invalidate_token(self) -> bool:
        """Verwirft ein OAuth-Token vor einem erneuten Versuch.

        Returns:
            ``True``, wenn ein neues Token beschafft werden kann (OAuth), sonst
            ``False`` (statisches Token lässt sich nicht erneuern).
        """
        if self._static_token is not None:
            return False
        self._access_token = None
        self._token_expires_at = 0.0
        return True

    # -- Antwortauswertung ----------------------------------------------

    def _parse_part(self, part: dict[str, object]) -> ProviderProduct:
        """Überführt einen Nexar-``SupPart`` in das neutrale Produktmodell."""
        parameters: dict[str, str] = {}
        specs: list[ProviderSpec] = []
        raw_specs = part.get("specs")
        if isinstance(raw_specs, list):
            for spec in raw_specs:
                if not isinstance(spec, dict):
                    continue
                attribute = spec.get("attribute")
                name = _nested_str(attribute, "name")
                shortname = _nested_str(attribute, "shortname")
                display_value = _optional_str(spec.get("displayValue"))
                if name is None or display_value is None:
                    continue
                parameters.setdefault(name, display_value)
                unit = _optional_str(spec.get("unitsSymbol")) or _optional_str(
                    spec.get("units")
                )
                specs.append(
                    ProviderSpec(
                        name=shortname or name,
                        display_value=display_value,
                        raw_value=_optional_str(spec.get("value")),
                        unit=unit,
                    )
                )

        return ProviderProduct(
            manufacturer_part_number=_optional_str(part.get("mpn")),
            manufacturer=_nested_str(part.get("manufacturer"), "name"),
            description=_optional_str(part.get("shortDescription")),
            category=_nested_str(part.get("category"), "name"),
            datasheet_url=_nested_str(part.get("bestDatasheet"), "url"),
            product_url=_optional_str(part.get("octopartUrl")),
            parameters=parameters,
            specs=tuple(specs),
        )

    def _parse_success(self, data: object) -> ProviderSearchResult:
        """Wertet erfolgreiche GraphQL-Daten (ohne ``errors``) aus."""
        search = _nested_get(data, "data", "supSearchMpn")
        results = search.get("results") if isinstance(search, dict) else None
        products: list[ProviderProduct] = []
        if isinstance(results, list):
            for result in results:
                if not isinstance(result, dict):
                    continue
                part = result.get("part")
                if isinstance(part, dict):
                    products.append(self._parse_part(part))
        return ProviderSearchResult(
            provider=self.name,
            status=ProviderResponseStatus.OK,
            products=tuple(products),
        )

    def search_exact(
        self,
        manufacturer_part_number: str,
        manufacturer: str | None = None,
    ) -> ProviderSearchResult:
        """Sucht bei Nexar nach einer Herstellerteilenummer (``supSearchMpn``).

        Args:
            manufacturer_part_number: Bereits technisch bereinigte
                Herstellerteilenummer.
            manufacturer: Optionaler Hersteller (nicht Teil der Anfrage, wird
                nachgelagert zur Plausibilitätsprüfung genutzt).

        Returns:
            Ein :class:`ProviderSearchResult`. Technische wie GraphQL-Fehler
            führen nicht zu einer Ausnahme, sondern zu einem entsprechenden
            Status.
        """
        variables: dict[str, Any] = {
            "mpn": manufacturer_part_number,
            "limit": self._limit,
            "country": self._country,
            "currency": self._currency,
            "rankingMethod": self._ranking_method,
            "distributorApiTimeout": self._distributor_api_timeout,
        }
        payload: dict[str, Any] = {
            "query": _MPN_SEARCH_QUERY,
            "variables": variables,
        }

        last_status = ProviderResponseStatus.API_ERROR
        last_error = "Anfrage fehlgeschlagen."
        for attempt in range(self._max_retries + 1):
            token = self._ensure_token()
            if token is None:
                last_status = ProviderResponseStatus.AUTH_ERROR
                last_error = "OAuth-Authentifizierung bei Nexar fehlgeschlagen."
            else:
                outcome = self._attempt(payload, token)
                if outcome.result is not None:
                    return outcome.result
                last_status, last_error = outcome.status, outcome.message
                if not outcome.retry:
                    return ProviderSearchResult(
                        provider=self.name,
                        status=last_status,
                        error_message=last_error,
                    )

            if attempt < self._max_retries:
                self._sleep(self._backoff_seconds * (2**attempt))

        return ProviderSearchResult(
            provider=self.name, status=last_status, error_message=last_error
        )

    def _attempt(self, payload: dict[str, Any], token: str) -> _Attempt:
        """Führt einen einzelnen GraphQL-Request aus und klassifiziert das Ergebnis."""
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = self._session.post(
                self._graphql_url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.Timeout as error:
            return _Attempt.retryable(
                ProviderResponseStatus.API_ERROR,
                self._redact(f"Zeitüberschreitung bei der Anfrage: {error}"),
            )
        except requests.RequestException as error:
            return _Attempt.retryable(
                ProviderResponseStatus.API_ERROR,
                self._redact(f"Verbindungsfehler bei der Anfrage: {error}"),
            )

        if response.status_code == 429:
            return _Attempt.retryable(
                ProviderResponseStatus.RATE_LIMITED, "Rate-Limit erreicht (HTTP 429)."
            )
        if response.status_code >= 500:
            return _Attempt.retryable(
                ProviderResponseStatus.API_ERROR,
                f"Serverfehler der Nexar-API (HTTP {response.status_code}).",
            )

        try:
            data = response.json()
        except ValueError:
            if response.status_code != 200:
                return _Attempt.terminal(
                    ProviderResponseStatus.API_ERROR,
                    f"Nexar-API antwortete mit HTTP {response.status_code}.",
                )
            return _Attempt.terminal(
                ProviderResponseStatus.API_ERROR,
                "Antwort der Nexar-API ist kein gültiges JSON.",
            )

        errors = data.get("errors") if isinstance(data, dict) else None
        if isinstance(errors, list) and errors:
            status, message = _classify_graphql_errors(errors)
            message = self._redact(message)
            if status is ProviderResponseStatus.AUTH_ERROR and self._invalidate_token():
                return _Attempt.retryable(status, message)
            return _Attempt.terminal(status, message)

        if response.status_code == 401:
            message = "Nexar-API: Authentifizierung abgelehnt (HTTP 401)."
            if self._invalidate_token():
                return _Attempt.retryable(
                    ProviderResponseStatus.AUTH_ERROR, message
                )
            # Statisches Token lässt sich nicht erneuern → kein sinnloser Retry.
            return _Attempt.terminal(ProviderResponseStatus.AUTH_ERROR, message)
        if response.status_code != 200:
            return _Attempt.terminal(
                ProviderResponseStatus.API_ERROR,
                f"Nexar-API antwortete mit HTTP {response.status_code}.",
            )

        return _Attempt.success(self._parse_success(data))


def _nested_get(container: object, *keys: str) -> object:
    """Liest einen verschachtelten Wert (ohne Typkonvertierung)."""
    current: object = container
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


class _Attempt:
    """Ergebnis eines einzelnen GraphQL-Versuchs (intern)."""

    __slots__ = ("status", "message", "retry", "result")

    def __init__(
        self,
        status: ProviderResponseStatus,
        message: str,
        *,
        retry: bool,
        result: ProviderSearchResult | None,
    ) -> None:
        self.status = status
        self.message = message
        self.retry = retry
        self.result = result

    @classmethod
    def success(cls, result: ProviderSearchResult) -> _Attempt:
        """Erfolgreicher Abruf."""
        return cls(ProviderResponseStatus.OK, "", retry=False, result=result)

    @classmethod
    def retryable(cls, status: ProviderResponseStatus, message: str) -> _Attempt:
        """Temporärer Fehler – ein weiterer Versuch ist sinnvoll."""
        return cls(status, message, retry=True, result=None)

    @classmethod
    def terminal(cls, status: ProviderResponseStatus, message: str) -> _Attempt:
        """Endgültiger Fehler – kein weiterer Versuch."""
        return cls(status, message, retry=False, result=None)
