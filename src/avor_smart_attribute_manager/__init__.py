"""AVOR Smart Attribute Manager.

Paketwurzel des Werkzeugs zur Analyse und qualitativen Verbesserung von
ERP-Artikelstammdaten in der Elektronikfertigung.

Grundprinzip des gesamten Pakets:

* Es werden ausschliesslich **Vorschläge** erzeugt.
* Originaldaten (ERP-Exporte) werden niemals automatisch verändert.
* Jede Empfehlung muss nachvollziehbar (begründbar) sein.

Dieses Modul enthält bewusst keine Geschäftslogik. Es stellt lediglich die
Paketmetadaten bereit und dient als Einstiegspunkt für die modulare Struktur.
"""

from __future__ import annotations

__all__ = ["__version__"]

#: Semantische Version des Pakets. Wird zentral hier gepflegt und von
#: ``pyproject.toml`` bzw. der Anwendung referenziert.
__version__ = "0.0.0"
