"""Excel-Import (Einlesen von ERP-Exporten).

Verantwortung:

* Öffnen und Einlesen von ERP-Excel-Exporten mit ``pandas``/``openpyxl``.
* Validieren der erwarteten Basisspalten.
* Normalisieren der Spaltennamen (siehe
  :mod:`avor_smart_attribute_manager.excel.columns`).
* Überführen der Rohdaten in die Domänenmodelle
  (:class:`avor_smart_attribute_manager.models.article.Article`).

Wichtige Regel: Dieses Modul arbeitet **ausschliesslich lesend**. Die
eingelesene Originaldatei wird niemals verändert oder überschrieben.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from avor_smart_attribute_manager.excel.columns import (
    ARTICLE_NUMBER_COLUMN,
    BASE_COLUMNS,
    SACHGRUPPE_COLUMN,
    normalize_columns,
)
from avor_smart_attribute_manager.models.article import Article


class MissingBaseColumnsError(ValueError):
    """Wird ausgelöst, wenn erwartete Basisspalten im Export fehlen."""


def read_workbook(path: Path) -> pd.DataFrame:
    """Liest einen ERP-Excel-Export ein (nur lesend).

    Args:
        path: Pfad zur Excel-Datei des ERP-Exports.

    Returns:
        Die eingelesenen Rohdaten als ``DataFrame`` (Spaltennamen unverändert).
    """
    return pd.read_excel(path, dtype=object)


def normalize_dataframe(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalisiert die Spaltennamen eines eingelesenen ``DataFrame``.

    Args:
        frame: Der eingelesene Roh-``DataFrame``.

    Returns:
        Ein neuer ``DataFrame`` mit normalisierten Spaltennamen. Der übergebene
        ``DataFrame`` wird nicht verändert.
    """
    renamed = frame.copy()
    renamed.columns = normalize_columns(str(column) for column in frame.columns)
    return renamed


def _require_base_columns(frame: pd.DataFrame) -> None:
    """Stellt sicher, dass alle Basisspalten vorhanden sind.

    Args:
        frame: Der zu prüfende ``DataFrame``.

    Raises:
        MissingBaseColumnsError: Wenn mindestens eine Basisspalte fehlt.
    """
    missing = [column for column in BASE_COLUMNS if column not in frame.columns]
    if missing:
        raise MissingBaseColumnsError(
            "Es fehlen erwartete Basisspalten: " + ", ".join(missing)
        )


def _clean_value(value: object) -> object | None:
    """Vereinheitlicht leere Werte zu ``None``.

    Args:
        value: Der ursprüngliche Zellenwert.

    Returns:
        ``None`` für leere Werte (``None``, ``NaN``, leerer/whitespace-String),
        sonst der unveränderte Wert.
    """
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def to_articles(frame: pd.DataFrame) -> list[Article]:
    """Wandelt einen normalisierten ``DataFrame`` in Artikelobjekte um.

    Args:
        frame: Ein ``DataFrame`` mit bereits normalisierten Spaltennamen.

    Returns:
        Liste der Artikel. Attributspalten sind alle Spalten ausser den
        Basisspalten; leere Attributwerte werden zu ``None`` vereinheitlicht.

    Raises:
        MissingBaseColumnsError: Wenn Basisspalten fehlen.
    """
    _require_base_columns(frame)

    attribute_columns = [
        str(column) for column in frame.columns if column not in BASE_COLUMNS
    ]

    articles: list[Article] = []
    for record in frame.to_dict(orient="records"):
        attributes = {
            column: _clean_value(record.get(column)) for column in attribute_columns
        }
        articles.append(
            Article(
                article_number=str(record[ARTICLE_NUMBER_COLUMN]).strip(),
                sachgruppenklasse=str(record[SACHGRUPPE_COLUMN]).strip(),
                attributes=attributes,
            )
        )
    return articles


def load_articles(path: Path) -> list[Article]:
    """Liest einen ERP-Export ein und liefert Artikelobjekte.

    Bündelt :func:`read_workbook`, :func:`normalize_dataframe` und
    :func:`to_articles` zu einem Schritt.

    Args:
        path: Pfad zur Excel-Datei des ERP-Exports.

    Returns:
        Liste der eingelesenen Artikel.

    Raises:
        MissingBaseColumnsError: Wenn erwartete Basisspalten fehlen.
    """
    frame = normalize_dataframe(read_workbook(path))
    return to_articles(frame)
