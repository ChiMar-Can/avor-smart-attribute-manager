"""Excel-Export der Analyseergebnisse (Schreiben **neuer** Dateien).

Verantwortung:

* Aus dem eingelesenen ERP-Export (unverändert) und den Prüfergebnissen eine
  neue Analyse-Excel-Datei erzeugen.
* Alle Originalspalten bleiben erhalten; die Analysespalten werden angefügt.
* Ein zusätzliches Tabellenblatt ``Zusammenfassung`` mit Kennzahlen.

Wichtige Regel: Es wird **immer** in eine neue Datei geschrieben. Die
Originaldatei des ERP-Exports wird niemals verändert oder überschrieben.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from avor_smart_attribute_manager.models.online import (
    ArticleOnlineStatus,
    AttributeSuggestion,
    ComparisonStatus,
    MatchConfidence,
    MatchStatus,
    ProviderComparison,
    SuggestionAction,
)
from avor_smart_attribute_manager.models.validation import (
    ArticleValidationResult,
    CheckStatus,
)

#: Name des Tabellenblatts mit den Artikel-Analysezeilen.
ANALYSIS_SHEET_NAME = "Analyse"

#: Name des Tabellenblatts mit den Kennzahlen.
SUMMARY_SHEET_NAME = "Zusammenfassung"

#: Suffix, das dem Dateinamen der Analysedatei angehängt wird.
ANALYSIS_SUFFIX = "_analyse"

#: Trennzeichen für die als Text ausgegebenen Attributlisten.
_LIST_SEPARATOR = ", "

#: Angefügte Analysespalten (Reihenfolge = Ausgabereihenfolge).
STATUS_COLUMN = "Pruefstatus"
ALLOWED_COLUMN = "Erlaubte_Attribute"
FILLED_COLUMN = "Gefuellte_Attribute"
MISSING_COLUMN = "Fehlende_Attribute"
DISALLOWED_COLUMN = "Nicht_erlaubte_gefuellte_Attribute"
MISSING_COUNT_COLUMN = "Anzahl_fehlender_Attribute"
DISALLOWED_COUNT_COLUMN = "Anzahl_unzulaessiger_Attribute"

ANALYSIS_COLUMNS: tuple[str, ...] = (
    STATUS_COLUMN,
    ALLOWED_COLUMN,
    FILLED_COLUMN,
    MISSING_COLUMN,
    DISALLOWED_COLUMN,
    MISSING_COUNT_COLUMN,
    DISALLOWED_COUNT_COLUMN,
)

#: Lesbare Bezeichnung je Prüfstatus (für die Spalte ``Pruefstatus``).
STATUS_LABELS: dict[CheckStatus, str] = {
    CheckStatus.OK: "OK",
    CheckStatus.UNKNOWN_SACHGRUPPE: "Unbekannte Sachgruppe",
    CheckStatus.ISSUES_FOUND: "Fehler gefunden",
}

#: Name des Tabellenblatts mit den Online-Attributvorschlägen.
ONLINE_SUGGESTIONS_SHEET_NAME = "Online_Vorschlaege"

#: Name des (optionalen) Tabellenblatts mit dem Suchstatus je Artikel.
ONLINE_STATUS_SHEET_NAME = "Online_Abgleich"

#: Name des Tabellenblatts mit dem Quellenvergleich (bei mehreren Providern).
PROVIDER_COMPARISON_SHEET_NAME = "Provider_Vergleich"

#: Lesbare Bezeichnung je Match-Status.
MATCH_STATUS_LABELS: dict[MatchStatus, str] = {
    MatchStatus.EXACT_MATCH: "Exakter Treffer",
    MatchStatus.MULTIPLE_EXACT_MATCHES: "Mehrere exakte Treffer",
    MatchStatus.MANUFACTURER_MISMATCH: "Herstellerabweichung",
    MatchStatus.NO_EXACT_MATCH: "Kein exakter Treffer",
    MatchStatus.NO_MPN: "Keine Herstellerteilenummer",
    MatchStatus.API_ERROR: "API-Fehler",
    MatchStatus.RATE_LIMITED: "Rate-Limit",
    MatchStatus.AUTH_ERROR: "Authentifizierungsfehler",
    MatchStatus.GRAPHQL_ERROR: "GraphQL-Fehler",
    MatchStatus.PART_LIMIT_REACHED: "Teilelimit erreicht",
}

#: Lesbare Bezeichnung je Quellenvergleichs-Status.
COMPARISON_STATUS_LABELS: dict[ComparisonStatus, str] = {
    ComparisonStatus.NO_TECHNICAL_DATA: "Keine technischen Daten",
    ComparisonStatus.ONLY_MOUSER_DATA: "Nur Mouser-Daten",
    ComparisonStatus.ONLY_DIGIKEY_DATA: "Nur DigiKey-Daten",
    ComparisonStatus.ONLY_NEXAR_DATA: "Nur Nexar-Daten",
    ComparisonStatus.SOURCES_AGREE: "Quellen stimmen überein",
    ComparisonStatus.MULTIPLE_STRUCTURED_SOURCES_AGREE: (
        "Mehrere strukturierte Quellen stimmen überein"
    ),
    ComparisonStatus.SOURCES_CONFLICT: "Quellen widersprechen sich",
}

#: Lesbare Bezeichnung je Konfidenzstufe.
CONFIDENCE_LABELS: dict[MatchConfidence, str] = {
    MatchConfidence.HOCH: "Hoch",
    MatchConfidence.MITTEL: "Mittel",
    MatchConfidence.NIEDRIG: "Niedrig",
}

#: Lesbare Bezeichnung je vorgeschlagener Aktion.
ACTION_LABELS: dict[SuggestionAction, str] = {
    SuggestionAction.ERGAENZEN: "Ergänzen",
    SuggestionAction.BESTAETIGT: "Bestätigt",
    SuggestionAction.KONFLIKT_PRUEFEN: "Konflikt prüfen",
}

#: Spaltenreihenfolge des Blattes ``Online_Vorschlaege``.
ONLINE_SUGGESTIONS_COLUMNS: tuple[str, ...] = (
    "ARTIKEL",
    "SachGruppe",
    "Hersteller",
    "HerstellerNr",
    "Provider",
    "Match_Status",
    "Match_Konfidenz",
    "Attribut",
    "ERP_Wert",
    "Vorschlag",
    "Aktion",
    "Konfidenz",
    "Rohwert",
    "Einheit",
    "Quelle_Parameter",
    "Produkt_URL",
    "Datenblatt_URL",
    "Begruendung",
)

#: Spaltenreihenfolge des Blattes ``Online_Abgleich``.
ONLINE_STATUS_COLUMNS: tuple[str, ...] = (
    "ARTIKEL",
    "SachGruppe",
    "Hersteller",
    "HerstellerNr",
    "Provider",
    "Match_Status",
    "Match_Konfidenz",
    "Gefundene_MPN",
    "Gefundener_Hersteller",
    "Produktkategorie",
    "Anzahl_Treffer",
    "Anzahl_strukturierter_Spezifikationen",
    "Produkt_URL",
    "Datenblatt_URL",
    "Meldung",
)

#: Spaltenreihenfolge des Blattes ``Provider_Vergleich``.
PROVIDER_COMPARISON_COLUMNS: tuple[str, ...] = (
    "ARTIKEL",
    "SachGruppe",
    "Hersteller",
    "HerstellerNr",
    "Vergleichsstatus",
    "Quellen_mit_Daten",
    "Uebereinstimmende_Attribute",
    "Abweichende_Attribute",
)


class RowCountMismatchError(ValueError):
    """Wird ausgelöst, wenn Zeilenzahl und Ergebnisanzahl nicht übereinstimmen."""


def analysis_output_path(input_path: Path) -> Path:
    """Bestimmt den Zielpfad der Analysedatei zu einem Eingabepfad.

    Args:
        input_path: Pfad der eingelesenen ERP-Excel-Datei.

    Returns:
        Pfad ``<Dateiname>_analyse.xlsx`` im selben Verzeichnis.
    """
    path = Path(input_path)
    return path.with_name(f"{path.stem}{ANALYSIS_SUFFIX}.xlsx")


def _join(values: Sequence[str]) -> str:
    """Verbindet Attributnamen zu einer kommagetrennten Zeichenkette."""
    return _LIST_SEPARATOR.join(values)


def build_analysis_frame(
    original: pd.DataFrame, results: Sequence[ArticleValidationResult]
) -> pd.DataFrame:
    """Erzeugt den Analyse-``DataFrame`` (Originalspalten + Analysespalten).

    Args:
        original: Der unveränderte, eingelesene ERP-``DataFrame`` (Originalspalten
            und -reihenfolge).
        results: Prüfergebnisse in derselben Reihenfolge wie die Zeilen.

    Returns:
        Ein neuer ``DataFrame`` mit allen Originalspalten und den angefügten
        Analysespalten. Der übergebene ``DataFrame`` wird nicht verändert.

    Raises:
        RowCountMismatchError: Wenn Zeilenzahl und Ergebnisanzahl abweichen.
    """
    if len(original) != len(results):
        raise RowCountMismatchError(
            f"Zeilenzahl ({len(original)}) und Ergebnisse ({len(results)}) "
            "stimmen nicht überein."
        )

    frame = original.copy()
    frame[STATUS_COLUMN] = [STATUS_LABELS[result.status] for result in results]
    frame[ALLOWED_COLUMN] = [_join(result.allowed_attributes) for result in results]
    frame[FILLED_COLUMN] = [_join(result.filled_attributes) for result in results]
    frame[MISSING_COLUMN] = [_join(result.missing_attributes) for result in results]
    frame[DISALLOWED_COLUMN] = [
        _join(result.disallowed_filled_attributes) for result in results
    ]
    frame[MISSING_COUNT_COLUMN] = [len(result.missing_attributes) for result in results]
    frame[DISALLOWED_COUNT_COLUMN] = [
        len(result.disallowed_filled_attributes) for result in results
    ]
    return frame


def build_summary_frame(results: Sequence[ArticleValidationResult]) -> pd.DataFrame:
    """Erzeugt den Kennzahlen-``DataFrame`` für das Zusammenfassungsblatt.

    Args:
        results: Prüfergebnisse je Artikel.

    Returns:
        Ein ``DataFrame`` mit den Spalten ``Kennzahl`` und ``Wert``.
    """
    total = len(results)
    ok = sum(1 for result in results if result.status is CheckStatus.OK)
    unknown = sum(
        1 for result in results if result.status is CheckStatus.UNKNOWN_SACHGRUPPE
    )
    with_missing = sum(1 for result in results if result.missing_attributes)
    with_disallowed = sum(
        1 for result in results if result.disallowed_filled_attributes
    )

    kennzahlen = [
        ("Anzahl Artikel", total),
        ("Anzahl OK", ok),
        ("Anzahl unbekannte Sachgruppen", unknown),
        ("Anzahl Artikel mit fehlenden Attributen", with_missing),
        ("Anzahl Artikel mit unzulässigen Attributen", with_disallowed),
    ]
    return pd.DataFrame(kennzahlen, columns=["Kennzahl", "Wert"])


def write_analysis_workbook(
    analysis: pd.DataFrame, summary: pd.DataFrame, output_path: Path
) -> None:
    """Schreibt Analyse und Zusammenfassung in eine neue Excel-Datei.

    Args:
        analysis: Der Analyse-``DataFrame`` (Originalspalten + Analysespalten).
        summary: Der Kennzahlen-``DataFrame``.
        output_path: Zielpfad der neu zu erzeugenden Datei.
    """
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        analysis.to_excel(writer, sheet_name=ANALYSIS_SHEET_NAME, index=False)
        summary.to_excel(writer, sheet_name=SUMMARY_SHEET_NAME, index=False)


def export_analysis(
    original: pd.DataFrame,
    results: Sequence[ArticleValidationResult],
    input_path: Path,
    output_path: Path | None = None,
) -> Path:
    """Erzeugt die vollständige Analysedatei zu einem ERP-Export.

    Args:
        original: Der unveränderte, eingelesene ERP-``DataFrame``.
        results: Prüfergebnisse in Zeilenreihenfolge.
        input_path: Pfad der Eingabedatei (für die Namensableitung).
        output_path: Optionaler expliziter Zielpfad; ohne Angabe wird
            ``<Dateiname>_analyse.xlsx`` verwendet.

    Returns:
        Der Pfad der geschriebenen Analysedatei.

    Raises:
        RowCountMismatchError: Wenn Zeilenzahl und Ergebnisanzahl abweichen.
    """
    target = output_path if output_path is not None else analysis_output_path(input_path)
    analysis = build_analysis_frame(original, results)
    summary = build_summary_frame(results)
    write_analysis_workbook(analysis, summary, target)
    return target


def build_online_suggestions_frame(
    suggestions: Sequence[AttributeSuggestion],
) -> pd.DataFrame:
    """Erzeugt den ``DataFrame`` für das Blatt ``Online_Vorschlaege``.

    Args:
        suggestions: Die erzeugten Attributvorschläge.

    Returns:
        Ein ``DataFrame`` mit der Spaltenreihenfolge
        :data:`ONLINE_SUGGESTIONS_COLUMNS` (leer, aber mit Kopfzeile, wenn keine
        Vorschläge vorliegen).
    """
    rows = [
        {
            "ARTIKEL": suggestion.article_number,
            "SachGruppe": suggestion.sachgruppe,
            "Hersteller": suggestion.source_manufacturer,
            "HerstellerNr": suggestion.source_mpn,
            "Provider": suggestion.provider,
            "Match_Status": MATCH_STATUS_LABELS[suggestion.match_status],
            "Match_Konfidenz": CONFIDENCE_LABELS[suggestion.confidence],
            "Attribut": suggestion.attribute,
            "ERP_Wert": suggestion.erp_value,
            "Vorschlag": suggestion.suggested_value,
            "Aktion": ACTION_LABELS[suggestion.action],
            "Konfidenz": CONFIDENCE_LABELS[suggestion.confidence],
            "Rohwert": suggestion.raw_value,
            "Einheit": suggestion.unit,
            "Quelle_Parameter": suggestion.source_parameter,
            "Produkt_URL": suggestion.product_url,
            "Datenblatt_URL": suggestion.datasheet_url,
            "Begruendung": suggestion.reason,
        }
        for suggestion in suggestions
    ]
    return pd.DataFrame(rows, columns=list(ONLINE_SUGGESTIONS_COLUMNS))


def build_online_status_frame(
    statuses: Sequence[ArticleOnlineStatus],
) -> pd.DataFrame:
    """Erzeugt den ``DataFrame`` für das Blatt ``Online_Abgleich``.

    Args:
        statuses: Ein Status je Artikel.

    Returns:
        Ein ``DataFrame`` mit der Spaltenreihenfolge :data:`ONLINE_STATUS_COLUMNS`.
    """
    rows = []
    for status in statuses:
        product = status.product
        confidence = (
            product.match_confidence
            if product is not None and product.match_confidence is not None
            else None
        )
        rows.append(
            {
                "ARTIKEL": status.article_number,
                "SachGruppe": status.sachgruppe,
                "Hersteller": status.manufacturer,
                "HerstellerNr": status.manufacturer_part_number,
                "Provider": status.provider,
                "Match_Status": MATCH_STATUS_LABELS[status.match_status],
                "Match_Konfidenz": (
                    CONFIDENCE_LABELS[confidence] if confidence is not None else None
                ),
                "Gefundene_MPN": product.found_mpn if product is not None else None,
                "Gefundener_Hersteller": (
                    product.found_manufacturer if product is not None else None
                ),
                "Produktkategorie": (
                    product.category if product is not None else None
                ),
                "Anzahl_Treffer": status.match_count,
                "Anzahl_strukturierter_Spezifikationen": (
                    len(product.raw_attributes) if product is not None else 0
                ),
                "Produkt_URL": product.product_url if product is not None else None,
                "Datenblatt_URL": (
                    product.datasheet_url if product is not None else None
                ),
                "Meldung": status.message,
            }
        )
    return pd.DataFrame(rows, columns=list(ONLINE_STATUS_COLUMNS))


def build_provider_comparison_frame(
    comparisons: Sequence[ProviderComparison],
) -> pd.DataFrame:
    """Erzeugt den ``DataFrame`` für das Blatt ``Provider_Vergleich``.

    Args:
        comparisons: Ein Quellenvergleich je Artikel.

    Returns:
        Ein ``DataFrame`` mit der Spaltenreihenfolge
        :data:`PROVIDER_COMPARISON_COLUMNS`.
    """
    rows = [
        {
            "ARTIKEL": comparison.article_number,
            "SachGruppe": comparison.sachgruppe,
            "Hersteller": comparison.manufacturer,
            "HerstellerNr": comparison.manufacturer_part_number,
            "Vergleichsstatus": COMPARISON_STATUS_LABELS[comparison.status],
            "Quellen_mit_Daten": _join(comparison.providers_with_data),
            "Uebereinstimmende_Attribute": _join(comparison.agreeing_attributes),
            "Abweichende_Attribute": _join(comparison.conflicting_attributes),
        }
        for comparison in comparisons
    ]
    return pd.DataFrame(rows, columns=list(PROVIDER_COMPARISON_COLUMNS))


def write_full_workbook(
    analysis: pd.DataFrame,
    summary: pd.DataFrame,
    online_suggestions: pd.DataFrame,
    online_status: pd.DataFrame,
    output_path: Path,
    comparison: pd.DataFrame | None = None,
) -> None:
    """Schreibt Analyse, Zusammenfassung und Online-Blätter in eine neue Datei.

    Die vorhandenen Blätter ``Analyse`` und ``Zusammenfassung`` bleiben erhalten;
    zusätzlich werden ``Online_Vorschlaege`` und ``Online_Abgleich`` sowie
    optional ``Provider_Vergleich`` geschrieben.

    Args:
        analysis: Der Analyse-``DataFrame``.
        summary: Der Kennzahlen-``DataFrame``.
        online_suggestions: Der ``DataFrame`` der Online-Vorschläge.
        online_status: Der ``DataFrame`` des Online-Abgleichstatus.
        output_path: Zielpfad der neu zu erzeugenden Datei.
        comparison: Optionaler ``DataFrame`` des Quellenvergleichs; wird nur
            geschrieben, wenn er übergeben wird.
    """
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        analysis.to_excel(writer, sheet_name=ANALYSIS_SHEET_NAME, index=False)
        summary.to_excel(writer, sheet_name=SUMMARY_SHEET_NAME, index=False)
        online_suggestions.to_excel(
            writer, sheet_name=ONLINE_SUGGESTIONS_SHEET_NAME, index=False
        )
        online_status.to_excel(
            writer, sheet_name=ONLINE_STATUS_SHEET_NAME, index=False
        )
        if comparison is not None:
            comparison.to_excel(
                writer, sheet_name=PROVIDER_COMPARISON_SHEET_NAME, index=False
            )


def export_analysis_with_online(
    original: pd.DataFrame,
    results: Sequence[ArticleValidationResult],
    suggestions: Sequence[AttributeSuggestion],
    statuses: Sequence[ArticleOnlineStatus],
    input_path: Path,
    output_path: Path | None = None,
    *,
    comparisons: Sequence[ProviderComparison] | None = None,
) -> Path:
    """Erzeugt die Analysedatei inklusive Online-Abgleich-Blättern.

    Args:
        original: Der unveränderte, eingelesene ERP-``DataFrame``.
        results: Prüfergebnisse in Zeilenreihenfolge.
        suggestions: Online-Attributvorschläge.
        statuses: Online-Abgleichstatus je Artikel.
        input_path: Pfad der Eingabedatei (für die Namensableitung).
        output_path: Optionaler expliziter Zielpfad; ohne Angabe wird
            ``<Dateiname>_analyse.xlsx`` verwendet.
        comparisons: Optionaler Quellenvergleich je Artikel; nur wenn nicht leer
            wird das Blatt ``Provider_Vergleich`` geschrieben.

    Returns:
        Der Pfad der geschriebenen Analysedatei.

    Raises:
        RowCountMismatchError: Wenn Zeilenzahl und Ergebnisanzahl abweichen.
    """
    target = output_path if output_path is not None else analysis_output_path(input_path)
    analysis = build_analysis_frame(original, results)
    summary = build_summary_frame(results)
    online_suggestions = build_online_suggestions_frame(suggestions)
    online_status = build_online_status_frame(statuses)
    comparison_frame = (
        build_provider_comparison_frame(comparisons)
        if comparisons
        else None
    )
    write_full_workbook(
        analysis,
        summary,
        online_suggestions,
        online_status,
        target,
        comparison_frame,
    )
    return target
