"""Excel-Import (Einlesen von ERP-Exporten).

Verantwortung:

* Öffnen und Einlesen von ERP-Excel-Exporten (voraussichtlich mit ``pandas``
  bzw. ``openpyxl``).
* Überführen der Rohdaten in die Domänenmodelle
  (:mod:`avor_smart_attribute_manager.models`).

Wichtige Regel: Dieses Modul arbeitet **nur lesend**. Die eingelesene
Originaldatei wird niemals verändert oder überschrieben.

Die konkrete Implementierung folgt später; die Funktion :func:`load_workbook`
ist ein Platzhalter.
"""

from __future__ import annotations

from pathlib import Path


def load_workbook(path: Path) -> object:
    """Liest einen ERP-Excel-Export ein (nur lesend).

    Args:
        path: Pfad zur Excel-Datei des ERP-Exports.

    Returns:
        Später eine strukturierte Repräsentation der eingelesenen Daten.

    Raises:
        NotImplementedError: Solange der Import noch nicht implementiert ist.
    """
    raise NotImplementedError("Excel-Import ist noch nicht implementiert.")
