"""Technische Normalisierung von Herstellerteilenummern und Herstellern.

Wichtig: Es findet **ausschliesslich** eine technische Bereinigung statt. Es
werden keine inhaltlichen Bestandteile der Herstellerteilenummer entfernt oder
interpretiert – insbesondere keine Gehäuse-, Verpackungs- oder Bestell-Suffixe
abgeschnitten. Erlaubt sind lediglich:

* Entfernen führender/nachfolgender Leerzeichen,
* Entfernen unsichtbarer Zeichen (z. B. Zero-Width-Space, BOM),
* Vereinheitlichung der Gross-/Kleinschreibung **nur für den Vergleich**.
"""

from __future__ import annotations

import unicodedata

#: Explizit zu entfernende unsichtbare Zeichen (Zero-Width & BOM).
_INVISIBLE_CHARS = (
    "\u200b",  # zero width space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\ufeff",  # zero width no-break space / BOM
    "\u00a0",  # no-break space
)


def _strip_invisible(value: str) -> str:
    """Entfernt unsichtbare/Steuerzeichen, ohne Inhalt zu interpretieren."""
    for char in _INVISIBLE_CHARS:
        value = value.replace(char, "")
    # Steuerzeichen (Kategorie "C…") entfernen, sichtbare Zeichen bleiben.
    return "".join(
        char for char in value if not unicodedata.category(char).startswith("C")
    )


def clean_part_number(value: str) -> str:
    """Bereinigt eine Herstellerteilenummer technisch (ohne Inhaltsverlust).

    Args:
        value: Ursprüngliche Herstellerteilenummer.

    Returns:
        Die bereinigte Herstellerteilenummer (Gross-/Kleinschreibung bleibt
        erhalten). Nur Rand-Leerzeichen und unsichtbare Zeichen werden entfernt.
    """
    return _strip_invisible(value).strip()


def part_number_key(value: str) -> str:
    """Erzeugt einen Vergleichsschlüssel für Herstellerteilenummern.

    Der Schlüssel dient ausschliesslich dem exakten Vergleich zweier
    Teilenummern. Er entfernt Rand-Leerzeichen und unsichtbare Zeichen und
    vereinheitlicht die Gross-/Kleinschreibung. Inhaltliche Bestandteile
    bleiben vollständig erhalten.

    Args:
        value: Ursprüngliche Herstellerteilenummer.

    Returns:
        Der normalisierte Vergleichsschlüssel.
    """
    return clean_part_number(value).casefold()


def manufacturer_key(value: str) -> str:
    """Erzeugt einen Vergleichsschlüssel für Herstellernamen.

    Args:
        value: Ursprünglicher Herstellername.

    Returns:
        Ein normalisierter Schlüssel (ohne Rand-/unsichtbare Zeichen,
        vereinheitlichte Gross-/Kleinschreibung, zusammengefasste Leerzeichen).
    """
    cleaned = _strip_invisible(value).strip().casefold()
    return " ".join(cleaned.split())
