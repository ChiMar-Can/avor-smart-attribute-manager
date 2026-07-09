"""Excel-Anbindung (Import und Export).

Kapselt sämtliche Lese- und Schreibvorgänge von Excel-Dateien und trennt sie
klar voneinander:

* :mod:`avor_smart_attribute_manager.excel.importer` – Einlesen von
  ERP-Exporten.
* :mod:`avor_smart_attribute_manager.excel.exporter` – Schreiben von
  Vorschlags-/Ergebnisdateien.

Zentrale Regel: Der Import liest ausschliesslich. Der Export schreibt immer in
**neue** Dateien und verändert niemals die Originaldatei des ERP-Exports.
"""

from __future__ import annotations

from avor_smart_attribute_manager.excel.importer import (
    MissingBaseColumnsError,
    load_articles,
    normalize_dataframe,
    read_workbook,
    to_articles,
)
from avor_smart_attribute_manager.excel.rule_catalog import (
    CatalogFormatError,
    read_attribute_catalog,
)

__all__ = [
    "CatalogFormatError",
    "MissingBaseColumnsError",
    "load_articles",
    "normalize_dataframe",
    "read_attribute_catalog",
    "read_workbook",
    "to_articles",
]
