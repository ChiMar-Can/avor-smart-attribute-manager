"""Vergleich von ERP- und Online-Attributwerten (Einheiten-Normalisierung).

Der Vergleich ist bewusst **konservativ**: Er vereinheitlicht lediglich
Schreibweisen (Gross-/Kleinschreibung, Leerzeichen, Dezimaltrennzeichen,
Einheitensymbole). Er interpretiert Werte nicht darüber hinaus. Dadurch werden
tatsächliche Übereinstimmungen zwar teils vorsichtig als „prüfen“ eingestuft,
aber echte Abweichungen niemals fälschlich als „bestätigt“ markiert.
"""

from __future__ import annotations

#: Vereinheitlichung einzelner Einheitensymbole (nur Schreibweise, kein Inhalt).
_SYMBOL_REPLACEMENTS = {
    "\u00b5": "u",  # micro sign
    "\u03bc": "u",  # greek small letter mu
    "\u2126": "ohm",  # ohm sign
    "\u03a9": "ohm",  # greek capital omega
    "\u03c9": "ohm",  # greek small omega (casefold of ohm sign)
}


def normalize_value(value: str) -> str:
    """Normalisiert einen Attributwert für den Vergleich.

    Args:
        value: Ursprünglicher Wert (ERP oder Quelle).

    Returns:
        Der normalisierte Wert (kleingeschrieben, ohne Leerzeichen,
        vereinheitlichte Symbole und Dezimaltrennzeichen).
    """
    text = value.strip().casefold()
    for symbol, replacement in _SYMBOL_REPLACEMENTS.items():
        text = text.replace(symbol, replacement)
    text = text.replace("ohms", "ohm")
    text = text.replace(",", ".")
    return "".join(text.split())


def values_match(erp_value: str, online_value: str) -> bool:
    """Prüft, ob zwei Werte nach Normalisierung übereinstimmen.

    Args:
        erp_value: Wert aus dem ERP.
        online_value: Wert aus der Datenquelle.

    Returns:
        ``True``, wenn die normalisierten Werte identisch sind, sonst ``False``.
    """
    return normalize_value(erp_value) == normalize_value(online_value)
