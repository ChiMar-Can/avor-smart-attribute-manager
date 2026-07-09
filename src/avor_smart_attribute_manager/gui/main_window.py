"""Hauptfenster der Anwendung.

Platzhalter für das zentrale Fenster (voraussichtlich abgeleitet von
``QMainWindow``). Es orchestriert die einzelnen Ansichten (siehe
:mod:`avor_smart_attribute_manager.gui.views`) und leitet Benutzeraktionen an
die Fachmodule weiter.

Die konkrete Qt-Implementierung folgt später. Dieses Modul importiert bewusst
noch kein PySide6, damit die Paketstruktur ohne installierte GUI-Bibliothek
importierbar bleibt (z. B. in einer reinen Test-/CI-Umgebung).
"""

from __future__ import annotations

__all__: list[str] = []
