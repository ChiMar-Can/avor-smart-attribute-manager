"""Allgemeine Provider-Schnittstelle für Bauteil-Datenquellen.

Definiert einen stabilen, provider-neutralen Vertrag, den konkrete Datenquellen
(z. B. Mouser, später DigiKey, Nexar, Hersteller-APIs oder eine interne
Parts-Datenbank) erfüllen. Die fachliche Analyse hängt ausschliesslich von
dieser Schnittstelle und den neutralen Ergebnismodellen ab – niemals von
provider-spezifischen Datenstrukturen.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class ProviderError(Exception):
    """Basisklasse für Fehler aus dem Provider-Umfeld."""


class MissingApiKeyError(ProviderError):
    """Wird ausgelöst, wenn ein benötigter API-Schlüssel fehlt."""


class ProviderResponseStatus(Enum):
    """Technischer Status einer Provider-Antwort (nicht der fachliche Match).

    Attributes:
        OK: Die Abfrage war technisch erfolgreich (auch ohne Treffer).
        API_ERROR: Ein technischer Fehler (Timeout, HTTP-Fehler, ungültige
            Antwort) ist aufgetreten.
        RATE_LIMITED: Die Datenquelle hat wegen eines Rate-Limits abgelehnt.
        AUTH_ERROR: Die Authentifizierung/Autorisierung schlug fehl (z. B.
            ungültiges oder abgelaufenes Token, das nicht erneuert werden konnte).
        GRAPHQL_ERROR: Eine GraphQL-Antwort enthielt ``errors`` (auch bei
            HTTP 200) und stellt damit **keinen** gültigen Produktabruf dar.
        PART_LIMIT_REACHED: Ein anbieterseitiges Abfrage-/Teilelimit wurde
            erreicht (z. B. Nexar-Kontingent).
    """

    OK = "ok"
    API_ERROR = "api_error"
    RATE_LIMITED = "rate_limited"
    AUTH_ERROR = "auth_error"
    GRAPHQL_ERROR = "graphql_error"
    PART_LIMIT_REACHED = "part_limit_reached"


@dataclass(frozen=True)
class ProviderSpec:
    """Eine strukturierte technische Spezifikation eines Produkts (neutralisiert).

    Ergänzt die einfache Name→Wert-Zuordnung (:attr:`ProviderProduct.parameters`)
    um die für Nachvollziehbarkeit benötigten Bestandteile: den Rohwert und die
    Einheit getrennt vom aufbereiteten Anzeigewert. Datenquellen, die keine
    getrennten Einheiten liefern (z. B. Mouser, DigiKey), lassen ``unit`` leer.

    Attributes:
        name: Name des Quellparameters (z. B. ``"Resistance"``).
        display_value: Aufbereiteter Anzeigewert inkl. Einheit (z. B. ``"10 kΩ"``).
        raw_value: Roher Zahlen-/Textwert ohne Einheit, falls getrennt verfügbar.
        unit: Einheitensymbol, falls getrennt verfügbar (z. B. ``"Ω"``).
    """

    name: str
    display_value: str
    raw_value: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class ProviderProduct:
    """Ein einzelner Produktdatensatz einer Datenquelle (neutralisiert).

    Attributes:
        manufacturer_part_number: Herstellerteilenummer laut Quelle.
        manufacturer: Hersteller laut Quelle.
        description: Produktbeschreibung der Quelle.
        category: Produktkategorie der Quelle.
        datasheet_url: URL des Datenblatts, falls vorhanden.
        product_url: URL der Produktseite, falls vorhanden.
        parameters: Strukturierte Produktparameter (Name → Anzeigewert).
        specs: Detailinformationen zu strukturierten Spezifikationen (mit
            Rohwert und Einheit), sofern die Quelle sie getrennt liefert. Ist
            optional und ergänzt :attr:`parameters` (identische Namen).
    """

    manufacturer_part_number: str | None
    manufacturer: str | None
    description: str | None = None
    category: str | None = None
    datasheet_url: str | None = None
    product_url: str | None = None
    parameters: Mapping[str, str] = field(default_factory=dict)
    specs: tuple[ProviderSpec, ...] = ()


@dataclass(frozen=True)
class ProviderSearchResult:
    """Neutrales Ergebnis einer Provider-Suche.

    Attributes:
        provider: Name des Providers (z. B. ``"mouser"``).
        status: Technischer Status der Antwort.
        products: Gefundene Produktdatensätze (leer bei Fehler/keinem Treffer).
        error_message: Verständliche Fehlermeldung, falls ``status`` einen
            Fehler anzeigt.
    """

    provider: str
    status: ProviderResponseStatus
    products: tuple[ProviderProduct, ...] = ()
    error_message: str | None = None


class ComponentDataProvider(ABC):
    """Abstrakte Datenquelle für die Suche nach Bauteilen.

    Konkrete Provider implementieren :meth:`search_exact`. Die Methode gibt
    immer ein :class:`ProviderSearchResult` zurück und wirft für technische
    Fehler **keine** Ausnahme, sondern setzt den entsprechenden
    :class:`ProviderResponseStatus`. Ausnahmen sind Konfigurationsfehler wie ein
    fehlender API-Schlüssel (:class:`MissingApiKeyError`).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Eindeutiger, kleingeschriebener Providername (z. B. ``"mouser"``)."""
        raise NotImplementedError

    @abstractmethod
    def search_exact(
        self,
        manufacturer_part_number: str,
        manufacturer: str | None = None,
    ) -> ProviderSearchResult:
        """Sucht Produkte zu einer Herstellerteilenummer.

        Args:
            manufacturer_part_number: Bereits technisch bereinigte
                Herstellerteilenummer.
            manufacturer: Optionaler Hersteller zur Plausibilitätsprüfung.

        Returns:
            Ein :class:`ProviderSearchResult` mit den (Roh-)Treffern der Quelle.
            Der fachliche exakte Abgleich erfolgt nachgelagert in der Analyse.
        """
        raise NotImplementedError
