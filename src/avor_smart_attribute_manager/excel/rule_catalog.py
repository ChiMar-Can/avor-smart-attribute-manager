"""Einlesen des Sachgruppen-/Attribut-Katalogs aus einer Excel-Datei.

Der Katalog ist eine gepflegte Excel-Liste mit den Spalten ``Sachgruppe`` und
``Attribut`` (eine Zeile je erlaubtem Attribut einer Sachgruppe). Aus diesem
Katalog wird das Regelwerk (``config/attribute_rules.json``) generiert.

Die Attributnamen werden dabei mit :func:`normalize_column_name` normalisiert,
damit sie exakt den Spaltennamen entsprechen, die der Import erzeugt.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from avor_smart_attribute_manager.excel.columns import normalize_column_name

#: Spalte des Katalogs mit dem Namen der Sachgruppenklasse.
CATALOG_SACHGRUPPE_COLUMN = "Sachgruppe"

#: Spalte des Katalogs mit dem (unnormalisierten) Attributnamen.
CATALOG_ATTRIBUTE_COLUMN = "Attribut"


class CatalogFormatError(ValueError):
    """Wird ausgelöst, wenn der Katalog nicht das erwartete Format hat."""


def _is_empty(value: object) -> bool:
    """Gibt an, ob ein Zellenwert als leer gilt."""
    if value is None:
        return True
    if isinstance(value, float):
        return bool(pd.isna(value))
    return isinstance(value, str) and value.strip() == ""


def read_attribute_catalog(path: Path) -> dict[str, list[str]]:
    """Liest den Attribut-Katalog und liefert die Zuordnung je Sachgruppe.

    Args:
        path: Pfad zur Katalog-Excel-Datei.

    Returns:
        Zuordnung von Sachgruppenklasse zu der Liste der (normalisierten)
        erlaubten Attribute. Die Reihenfolge der Sachgruppen und Attribute
        entspricht der Reihenfolge im Katalog; Duplikate werden entfernt.

    Raises:
        CatalogFormatError: Wenn die erwarteten Spalten fehlen.
    """
    frame = pd.read_excel(path, sheet_name=0, dtype=str)

    missing = [
        column
        for column in (CATALOG_SACHGRUPPE_COLUMN, CATALOG_ATTRIBUTE_COLUMN)
        if column not in frame.columns
    ]
    if missing:
        raise CatalogFormatError(
            "Im Katalog fehlen erwartete Spalten: " + ", ".join(missing)
        )

    mapping: dict[str, list[str]] = {}
    for raw_sachgruppe, raw_attribute in zip(
        frame[CATALOG_SACHGRUPPE_COLUMN], frame[CATALOG_ATTRIBUTE_COLUMN], strict=True
    ):
        if _is_empty(raw_sachgruppe) or _is_empty(raw_attribute):
            continue

        sachgruppe = str(raw_sachgruppe).strip()
        attribute = normalize_column_name(str(raw_attribute))

        attributes = mapping.setdefault(sachgruppe, [])
        if attribute not in attributes:
            attributes.append(attribute)

    return mapping
