"""Domänenmodelle (gemeinsame Datenstrukturen).

Enthält die zentralen, technologie-neutralen Datenstrukturen der Anwendung
(z. B. Artikel, Attribut, Analyseergebnis, Vorschlag). Diese Modelle werden
von mehreren Modulen gemeinsam genutzt und bilden das gemeinsame Vokabular
zwischen GUI, Analyse, Regelprüfung und Datenquellen.

Vorteil einer eigenen Modellschicht:

* Entkoppelt die fachlichen Begriffe von konkreten Bibliotheken (z. B. pandas
  oder PySide6).
* Erlaubt typsichere Schnittstellen zwischen den Modulen.

Konkrete Felder werden bewusst noch nicht festgelegt, um keine Annahmen über
die reale ERP-Datenstruktur zu treffen.
"""

from __future__ import annotations

__all__: list[str] = []
