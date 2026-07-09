"""Generiert das Regelwerk (JSON) aus dem Attribut-Katalog (Excel).

Aufruf (aus dem Projektwurzelverzeichnis, mit aktivierter Umgebung)::

    python scripts/generate_attribute_rules.py

Ohne Argumente werden die Standardpfade verwendet:

* Eingabe: ``data/attribute_catalog/20260706_Attribute.xlsx``
* Ausgabe: ``src/avor_smart_attribute_manager/config/attribute_rules.json``

Das Skript verändert ausschliesslich die Ausgabedatei und liest den Katalog nur.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from avor_smart_attribute_manager.excel.rule_catalog import read_attribute_catalog
from avor_smart_attribute_manager.rules.attribute_rules import (
    rules_document_from_mapping,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CATALOG = _REPO_ROOT / "data" / "attribute_catalog" / "20260706_Attribute.xlsx"
_DEFAULT_OUTPUT = (
    _REPO_ROOT
    / "src"
    / "avor_smart_attribute_manager"
    / "config"
    / "attribute_rules.json"
)


def generate(catalog_path: Path, output_path: Path) -> int:
    """Liest den Katalog und schreibt das Regelwerk als JSON.

    Args:
        catalog_path: Pfad zur Katalog-Excel-Datei (nur lesend).
        output_path: Zielpfad der zu schreibenden JSON-Datei.

    Returns:
        Anzahl der geschriebenen Sachgruppen.
    """
    mapping = read_attribute_catalog(catalog_path)
    document = rules_document_from_mapping(mapping)
    output_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(mapping)


def main() -> None:
    """Kommandozeilen-Einstiegspunkt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=_DEFAULT_CATALOG, help="Katalog-Excel-Datei"
    )
    parser.add_argument(
        "--output", type=Path, default=_DEFAULT_OUTPUT, help="Ziel-JSON-Datei"
    )
    args = parser.parse_args()

    count = generate(args.catalog, args.output)
    print(f"{count} Sachgruppen nach {args.output} geschrieben.")


if __name__ == "__main__":
    main()
