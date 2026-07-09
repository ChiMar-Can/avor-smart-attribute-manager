"""Anwendungseinstellungen.

Definiert die Struktur der Konfiguration und stellt Funktionen zum Laden der
Einstellungen bereit. Die konkrete Implementierung (z. B. Einlesen aus einer
Konfigurationsdatei oder aus Umgebungsvariablen) folgt später.

Designidee:

* Eine zentrale, klar typisierte Einstellungsstruktur (z. B. ein
  ``dataclass``), damit die restliche Anwendung typsicher auf Konfiguration
  zugreifen kann.
* Standardwerte im Code, Überschreibungen aus externer Quelle.

Dieses Modul enthält bewusst noch keine konkreten Feldwerte, um keine
Annahmen über den späteren Funktionsumfang zu treffen.
"""

from __future__ import annotations


def load_settings() -> object:
    """Lädt die Anwendungseinstellungen.

    Platzhalter. Liefert später ein typisiertes Einstellungsobjekt.

    Raises:
        NotImplementedError: Solange das Laden der Konfiguration noch nicht
            implementiert ist.
    """
    raise NotImplementedError("Konfigurations-Laden ist noch nicht implementiert.")
