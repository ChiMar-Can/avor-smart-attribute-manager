"""Anwendungs-Bootstrap (Zusammenbau der Komponenten).

Dieses Modul ist die zentrale Stelle, an der die einzelnen Bausteine der
Anwendung verdrahtet werden (Konfiguration laden, GUI starten, Dienste
bereitstellen). Es bildet die Grenze zwischen dem reinen Programmstart und
der eigentlichen Anwendungslogik.

Verantwortung:

* Konfiguration aus :mod:`avor_smart_attribute_manager.config` laden.
* Die GUI (siehe :mod:`avor_smart_attribute_manager.gui`) initialisieren und
  starten.
* Abhängigkeiten (z. B. Excel-Import/-Export, Analyse) zusammenführen und der
  GUI zur Verfügung stellen (Dependency Injection).

Hier befindet sich bewusst **keine** Geschäftslogik – lediglich der
Zusammenbau. Solange es noch keine GUI gibt, delegiert :func:`run` an die
Kommandozeilenanwendung (:mod:`avor_smart_attribute_manager.cli`).
"""

from __future__ import annotations

from avor_smart_attribute_manager.cli import main


def run(argv: list[str] | None = None) -> int:
    """Startet die Anwendung.

    Aktuell existiert noch keine GUI; der Start delegiert daher an die
    Kommandozeilenanwendung.

    Args:
        argv: Optionale Argumentliste (vor allem für Tests).

    Returns:
        Prozess-Exit-Code (``0`` bei Erfolg).
    """
    return main(argv)
