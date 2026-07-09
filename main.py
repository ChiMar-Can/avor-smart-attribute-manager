"""Bequemer Einstiegspunkt für die Kommandozeile.

Ermöglicht den Aufruf ``python main.py analyse "ERP_Export.xlsx"`` bzw.
``python main.py`` (mit Dateiauswahl). Die eigentliche Logik liegt im Paket
:mod:`avor_smart_attribute_manager.cli`.
"""

from __future__ import annotations

from avor_smart_attribute_manager.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
