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
Zusammenbau. Die Funktion :func:`run` ist derzeit ein Platzhalter.
"""

from __future__ import annotations


def run() -> int:
    """Startet die Anwendung.

    Platzhalter für den späteren Programmstart. Die konkrete Implementierung
    (GUI hochfahren, Konfiguration laden, Ereignisschleife starten) folgt in
    einem späteren Entwicklungsschritt.

    Returns:
        Beabsichtigter Prozess-Exit-Code (``0`` bei Erfolg).

    Raises:
        NotImplementedError: Solange der Anwendungsstart noch nicht
            implementiert ist.
    """
    raise NotImplementedError("Anwendungsstart ist noch nicht implementiert.")
