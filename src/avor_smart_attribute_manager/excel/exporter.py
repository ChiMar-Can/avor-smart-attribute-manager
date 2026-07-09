"""Excel-Export (Schreiben von Vorschlags-/Ergebnisdateien).

Verantwortung:

* Schreiben der erzeugten Vorschläge und Analyseergebnisse in eine Excel-Datei
  (voraussichtlich mit ``xlsxwriter`` bzw. ``openpyxl``).

Wichtige Regel: Es wird **immer** in eine neue Datei geschrieben. Die
Originaldatei des ERP-Exports wird niemals verändert oder überschrieben.

Die konkrete Implementierung folgt später; die Funktion :func:`write_workbook`
ist ein Platzhalter.
"""

from __future__ import annotations

from pathlib import Path


def write_workbook(data: object, path: Path) -> None:
    """Schreibt Ergebnisse/Vorschläge in eine neue Excel-Datei.

    Args:
        data: Die zu exportierenden Vorschläge/Ergebnisse.
        path: Zielpfad der neu zu erzeugenden Datei.

    Raises:
        NotImplementedError: Solange der Export noch nicht implementiert ist.
    """
    raise NotImplementedError("Excel-Export ist noch nicht implementiert.")
