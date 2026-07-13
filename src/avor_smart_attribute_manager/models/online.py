"""Domänenmodelle für den Online-Abgleich anhand der Herstellerteilenummer.

Diese Modelle sind bewusst technologie- und provider-neutral. Konkrete
Datenquellen (z. B. Mouser) liefern ihre Rohantworten über die Provider-
Schnittstelle (:mod:`avor_smart_attribute_manager.datasources`) und werden in
diese neutralen Strukturen überführt. Die fachliche Analyse hängt dadurch nicht
von einer konkreten API ab.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    """Ergebnis des exakten Abgleichs zwischen ERP und Datenquelle.

    Attributes:
        EXACT_MATCH: Genau ein Datensatz stimmt nach technischer Normalisierung
            exakt in der Herstellerteilenummer (und – sofern im ERP vorhanden –
            im Hersteller) überein.
        MULTIPLE_EXACT_MATCHES: Mehrere Datensätze stimmen exakt überein; es
            darf kein Wert automatisch als sicher gelten.
        MANUFACTURER_MISMATCH: Die Herstellerteilenummer passt, aber der im ERP
            hinterlegte Hersteller weicht ab.
        NO_EXACT_MATCH: Kein Datensatz stimmt exakt in der Herstellerteilenummer
            überein (ein blosser Suchtreffer genügt nicht).
        NO_MPN: Der Artikel besitzt keine (verwertbare) Herstellerteilenummer;
            es wurde nicht gesucht.
        API_ERROR: Die Abfrage ist mit einem technischen Fehler fehlgeschlagen.
        RATE_LIMITED: Die Datenquelle hat wegen eines Rate-Limits abgelehnt.
    """

    EXACT_MATCH = "exact_match"
    MULTIPLE_EXACT_MATCHES = "multiple_exact_matches"
    MANUFACTURER_MISMATCH = "manufacturer_mismatch"
    NO_EXACT_MATCH = "no_exact_match"
    NO_MPN = "no_mpn"
    API_ERROR = "api_error"
    RATE_LIMITED = "rate_limited"


class MatchConfidence(Enum):
    """Nachvollziehbare, regelbasierte Konfidenzstufe eines Vorschlags.

    Attributes:
        HOCH: Exakte Herstellerteilenummer, Hersteller stimmt überein, genau ein
            eindeutiger Datensatz, Wert aus strukturiertem Produktparameter.
        MITTEL: Exakte Herstellerteilenummer, Hersteller im ERP nicht vorhanden,
            genau ein plausibler Treffer, Wert aus strukturiertem Parameter.
        NIEDRIG: Mehrere exakte Treffer, Herstellerabweichung oder unsichere
            Zuordnung. Solche Vorschläge sind ausschliesslich Prüfhinweise.
    """

    HOCH = "hoch"
    MITTEL = "mittel"
    NIEDRIG = "niedrig"


#: Match-Status, die überhaupt einen exakten oder plausiblen Treffer darstellen.
MATCH_STATUSES_WITH_HIT = frozenset(
    {
        MatchStatus.EXACT_MATCH,
        MatchStatus.MULTIPLE_EXACT_MATCHES,
        MatchStatus.MANUFACTURER_MISMATCH,
    }
)


@dataclass(frozen=True)
class ProductInfo:
    """Neutrales Produktdatenmodell einer Online-Abfrage.

    Enthält die für die Analyse relevanten, aufbereiteten Felder eines
    gefundenen Produkts. Die vollständige Rohantwort der Datenquelle wird
    **nicht** hier gehalten und **nicht** in die Ergebnis-Excel geschrieben; sie
    kann für Debugging/Tests separat protokolliert werden (ohne Zugangsdaten).

    Attributes:
        erp_article_number: Artikelnummer aus dem ERP-Export.
        requested_mpn: Angefragte (bereinigte) Herstellerteilenummer.
        requested_manufacturer: Angefragter Hersteller (falls im ERP vorhanden).
        found_mpn: Vom Provider gelieferte Herstellerteilenummer.
        found_manufacturer: Vom Provider gelieferter Hersteller.
        description: Produktbeschreibung der Quelle.
        category: Produktkategorie der Quelle.
        datasheet_url: URL des Datenblatts, falls vorhanden.
        product_url: URL der Produktseite, falls vorhanden.
        raw_attributes: Strukturierte Rohattribute der Quelle
            (Parametername → Wert), bereits ohne Zugangsdaten.
        provider: Name des Providers (z. B. ``"mouser"``).
        retrieved_at: Zeitpunkt des Abrufs.
        match_status: Ergebnis des exakten Abgleichs.
        match_confidence: Konfidenz des Treffers (falls zutreffend).
    """

    erp_article_number: str
    requested_mpn: str
    requested_manufacturer: str | None
    found_mpn: str | None
    found_manufacturer: str | None
    description: str | None
    category: str | None
    datasheet_url: str | None
    product_url: str | None
    raw_attributes: Mapping[str, str]
    provider: str
    retrieved_at: datetime
    match_status: MatchStatus
    match_confidence: MatchConfidence | None = None


@dataclass(frozen=True)
class ArticleOnlineStatus:
    """Allgemeiner Online-Abgleichstatus je Artikel (eine Zeile pro Artikel).

    Attributes:
        article_number: ERP-Artikelnummer.
        sachgruppe: Sachgruppe des Artikels (zur Nachvollziehbarkeit).
        manufacturer: Im ERP hinterlegter Hersteller (falls vorhanden).
        manufacturer_part_number: Bereinigte, angefragte Herstellerteilenummer.
        provider: Verwendeter Provider.
        match_status: Ergebnis des Abgleichs.
        match_count: Anzahl exakter Treffer (nach Normalisierung).
        message: Optionale, verständliche Zusatzinformation (z. B. Fehlertext).
        product: Neutrales Produktdatenmodell des primären Treffers (falls
            vorhanden).
    """

    article_number: str
    sachgruppe: str
    manufacturer: str | None
    manufacturer_part_number: str | None
    provider: str
    match_status: MatchStatus
    match_count: int = 0
    message: str | None = None
    product: ProductInfo | None = None


@dataclass(frozen=True)
class OnlineAnalysis:
    """Gesamtergebnis eines Online-Abgleichlaufs.

    Attributes:
        statuses: Ein Status je Artikel (Reihenfolge wie die Eingabe).
        suggestions: Alle erzeugten Attributvorschläge.
    """

    statuses: list[ArticleOnlineStatus] = field(default_factory=list)
    suggestions: list[AttributeSuggestion] = field(default_factory=list)


class SuggestionAction(Enum):
    """Empfohlene Aktion für ein einzelnes Attribut.

    Attributes:
        ERGAENZEN: ERP-Wert leer, Online-Wert vorhanden → Ergänzung vorschlagen.
        BESTAETIGT: ERP-Wert und Online-Wert stimmen (nach Normalisierung)
            überein → bestätigt.
        KONFLIKT_PRUEFEN: ERP-Wert und Online-Wert weichen ab → manuell prüfen.
    """

    ERGAENZEN = "ergaenzen"
    BESTAETIGT = "bestaetigt"
    KONFLIKT_PRUEFEN = "konflikt_pruefen"


@dataclass(frozen=True)
class AttributeSuggestion:
    """Ein nachvollziehbarer Vorschlag für genau ein Attribut eines Artikels.

    Bestehende ERP-Werte werden dadurch niemals verändert; es handelt sich
    ausschliesslich um einen Vorschlag mit Quelle und Begründung.

    Attributes:
        article_number: ERP-Artikelnummer.
        sachgruppe: Sachgruppe des Artikels.
        attribute: Betroffenes (internes) Attribut.
        erp_value: Aktueller ERP-Wert (oder ``None``, wenn leer).
        suggested_value: Vorgeschlagener bzw. bestätigter Wert aus der Quelle.
        action: Empfohlene Aktion (siehe :class:`SuggestionAction`).
        provider: Datenquelle des Vorschlags.
        source_mpn: Herstellerteilenummer der Quelle.
        source_manufacturer: Hersteller der Quelle.
        match_status: Match-Status des zugrundeliegenden Treffers.
        confidence: Konfidenzstufe des Vorschlags.
        product_url: Produkt-URL der Quelle (falls vorhanden).
        datasheet_url: Datenblatt-URL der Quelle (falls vorhanden).
        reason: Verständliche Begründung des Vorschlags.
    """

    article_number: str
    sachgruppe: str
    attribute: str
    erp_value: str | None
    suggested_value: str
    action: SuggestionAction
    provider: str
    source_mpn: str | None
    source_manufacturer: str | None
    match_status: MatchStatus
    confidence: MatchConfidence
    product_url: str | None
    datasheet_url: str | None
    reason: str
