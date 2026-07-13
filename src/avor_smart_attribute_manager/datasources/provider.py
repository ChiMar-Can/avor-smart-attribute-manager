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
    """

    OK = "ok"
    API_ERROR = "api_error"
    RATE_LIMITED = "rate_limited"


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
        parameters: Strukturierte Produktparameter (Name → Wert).
    """

    manufacturer_part_number: str | None
    manufacturer: str | None
    description: str | None = None
    category: str | None = None
    datasheet_url: str | None = None
    product_url: str | None = None
    parameters: Mapping[str, str] = field(default_factory=dict)


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
