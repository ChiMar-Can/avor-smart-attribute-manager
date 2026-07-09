"""Spaltendefinitionen und -normalisierung für ERP-Excel-Exporte.

Dieses Modul hält die Namen der erwarteten Basisspalten sowie die
Normalisierungsregeln für Attributspalten zentral vor. Dadurch stehen die
Spaltennamen nicht verstreut im Code und lassen sich leicht pflegen.

Normalisierung bedeutet hier ausschliesslich das Vereinheitlichen von
*Spaltennamen* (nicht von Werten), z. B. das Korrigieren von Schreibweisen und
das Entfernen von Sonderzeichen. Die Zuordnung ist explizit und wird bewusst
nicht geraten.
"""

from __future__ import annotations

from collections.abc import Iterable

#: Spalte mit der eindeutigen Artikelnummer.
ARTICLE_NUMBER_COLUMN = "ARTIKELNUMMER"

#: Spalte mit der Sachgruppenklasse, anhand derer das Regelwerk greift.
SACHGRUPPE_COLUMN = "SACHGRUPPENKLASSE"

#: Basisspalten, die in jedem ERP-Export vorhanden sein müssen.
BASE_COLUMNS: tuple[str, ...] = (ARTICLE_NUMBER_COLUMN, SACHGRUPPE_COLUMN)

#: Explizite Zuordnung von ERP-Spaltennamen zu normalisierten Attributnamen.
#: Nur hier aufgeführte Spalten werden umbenannt; alle übrigen bleiben
#: unverändert.
COLUMN_RENAME_MAP: dict[str, str] = {
    "Dimmension": "Dimension",
    "SMD-Bauform": "SmdBauform",
    "Feeder-Typ": "Feeder",
    "Spannung-Primär": "Spannungprimaer",
    "Strom-Primär": "Stromprimaer",
    "Spannung-Sekundär": "Spannungsekundaer",
    "Strom-Sekundär": "Stromsekundaer",
    "Länge": "Laengeattribut",
    "Nutzengrösse": "Nutzengroesse",
    "Widerstand": "Widerstandattribut",
}


def normalize_column_name(name: str) -> str:
    """Normalisiert einen einzelnen Spaltennamen.

    Args:
        name: Ursprünglicher Spaltenname aus dem ERP-Export.

    Returns:
        Der normalisierte Name gemäss :data:`COLUMN_RENAME_MAP`; unbekannte
        Namen werden unverändert (aber ohne umschliessende Leerzeichen)
        zurückgegeben.
    """
    stripped = name.strip()
    return COLUMN_RENAME_MAP.get(stripped, stripped)


def normalize_columns(columns: Iterable[str]) -> list[str]:
    """Normalisiert eine Folge von Spaltennamen.

    Args:
        columns: Ursprüngliche Spaltennamen.

    Returns:
        Liste der normalisierten Spaltennamen in unveränderter Reihenfolge.
    """
    return [normalize_column_name(column) for column in columns]
