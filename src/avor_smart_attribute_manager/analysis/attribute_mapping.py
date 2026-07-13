"""Sachgruppenabhängiges Mapping strukturierter Quellparameter auf ERP-Attribute.

Wandelt strukturierte Produktparameter einer Datenquelle (z. B. Mouser) in die
internen ERP-Attribute um. Grundregeln:

* Das Mapping erfolgt **sachgruppenabhängig** (z. B. bedeutet ``Wert`` bei einem
  Widerstand den Widerstandswert, bei einem Kondensator die Kapazität).
* Es werden **nur** Attribute vorgeschlagen, die laut Regelwerk für die
  jeweilige Sachgruppe erlaubt sind.
* Nicht eindeutig zuordenbare Quellparameter werden **nicht geraten**.

Das Mapping ist bewusst konservativ und leicht erweiterbar gehalten.
"""

from __future__ import annotations

from collections.abc import Mapping

#: Interne ERP-Attribute, die in diesem Schritt unterstützt werden.
SUPPORTED_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "Technologie",
        "Typ",
        "Bauform",
        "SmdBauform",
        "Wert",
        "Toleranz",
        "Dielektrikum",
        "Spannung",
        "Strom",
        "Leistung",
        "Bemerkung",
    }
)

#: Zuordnung normalisierter Quellparameter-Namen zu internen Attributen
#: (sachgruppenunabhängig). Die Reihenfolge bestimmt die Priorität: Der erste
#: passende Parameter je Attribut gewinnt.
COMMON_PARAMETER_MAP: dict[str, str] = {
    "tolerance": "Toleranz",
    "dielectric": "Dielektrikum",
    "dielectric characteristic": "Dielektrikum",
    "voltage rating": "Spannung",
    "voltage rating dc": "Spannung",
    "voltage rating (dc)": "Spannung",
    "voltage - rated": "Spannung",
    "voltage": "Spannung",
    "current rating": "Strom",
    "current - rated": "Strom",
    "current": "Strom",
    "power rating": "Leistung",
    "power (watts)": "Leistung",
    "power - max": "Leistung",
    "power": "Leistung",
    "mounting style": "Technologie",
    "mounting type": "Technologie",
    "package / case": "Bauform",
    "supplier device package": "Bauform",
    "case code (imperial)": "SmdBauform",
    "case code - in": "SmdBauform",
}

#: Sachgruppenabhängige Quellparameter, die auf das generische Attribut ``Wert``
#: abgebildet werden (normalisierte Parameternamen, Priorität nach Reihenfolge).
SACHGRUPPE_VALUE_PARAMETERS: dict[str, tuple[str, ...]] = {
    "Widerstand": ("resistance",),
    "Kondensator": ("capacitance",),
    "Ferrit Induktion Filter": ("inductance",),
    "Quarz Oszillator Resonator": ("frequency",),
}


def _normalize_parameter_name(name: str) -> str:
    """Vereinheitlicht einen Quellparameter-Namen für den Mapping-Vergleich."""
    return " ".join(name.strip().casefold().split())


def map_parameters(
    parameters: Mapping[str, str],
    sachgruppe: str,
    allowed_attributes: frozenset[str] | set[str] | tuple[str, ...],
) -> dict[str, str]:
    """Bildet Quellparameter auf erlaubte interne Attribute ab.

    Args:
        parameters: Strukturierte Quellparameter (Name → Wert).
        sachgruppe: Sachgruppe des Artikels (steuert das ``Wert``-Mapping).
        allowed_attributes: Für die Sachgruppe laut Regelwerk erlaubte Attribute.

    Returns:
        Zuordnung interner Attributnamen zu vorgeschlagenen Werten. Enthält nur
        Attribute, die sowohl erlaubt als auch eindeutig zuordenbar sind.
    """
    allowed = set(allowed_attributes)
    normalized: dict[str, str] = {}
    for raw_name, value in parameters.items():
        key = _normalize_parameter_name(raw_name)
        if key and key not in normalized:
            normalized[key] = value

    mapped: dict[str, str] = {}

    if "Wert" in allowed:
        for param in SACHGRUPPE_VALUE_PARAMETERS.get(sachgruppe, ()):
            if param in normalized:
                mapped["Wert"] = normalized[param]
                break

    for param_key, attribute in COMMON_PARAMETER_MAP.items():
        if attribute in allowed and attribute not in mapped and param_key in normalized:
            mapped[attribute] = normalized[param_key]

    return mapped
