"""Sachgruppenabhängiges Mapping strukturierter Quellparameter auf ERP-Attribute.

Wandelt strukturierte Produktparameter einer Datenquelle (z. B. Mouser, DigiKey,
Nexar) in die internen ERP-Attribute um. Grundregeln:

* Das Mapping erfolgt **sachgruppenabhängig** (z. B. bedeutet ``Wert`` bei einem
  Widerstand den Widerstandswert, bei einem Kondensator die Kapazität).
* Es werden **nur** Attribute vorgeschlagen, die laut Regelwerk für die
  jeweilige Sachgruppe erlaubt sind.
* Es werden **ausschliesslich** strukturierte Parameter verwendet; Freitext
  (Beschreibung, Benennung, Bemerkung) wird **nie** als Quelle genutzt.
* Nicht eindeutig zuordenbare Quellparameter werden **nicht geraten**.

Für Mouser/DigiKey greift ein generisches, im Code gepflegtes Mapping. Für Nexar
wird das Mapping datengetrieben aus
``config/provider_mappings/nexar_attribute_mapping.json`` geladen, damit es ohne
Code-Änderung erweitert werden kann.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path

from avor_smart_attribute_manager.datasources.provider import (
    ProviderProduct,
    ProviderSpec,
)

#: Zulässige Typen für die Menge erlaubter Attribute.
AllowedAttributes = frozenset[str] | set[str] | tuple[str, ...]

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

#: Paket, das die Provider-Mapping-Konfigurationen als Paketdaten enthält.
_MAPPING_PACKAGE = "avor_smart_attribute_manager.config.provider_mappings"

#: Dateiname der zentralen Nexar-Mapping-Konfiguration.
NEXAR_MAPPING_FILENAME = "nexar_attribute_mapping.json"


@dataclass(frozen=True)
class MappedAttribute:
    """Ergebnis des Mappings eines Quellparameters auf ein ERP-Attribut.

    Attributes:
        attribute: Internes ERP-Zielattribut.
        value: Vorgeschlagener (aufbereiteter) Wert.
        source_parameter: Name des Quellparameters (Nachvollziehbarkeit).
        raw_value: Roher Quellwert vor der Aufbereitung (falls verfügbar).
        unit: Einheit des Quellwerts (falls die Quelle sie getrennt liefert).
    """

    attribute: str
    value: str
    source_parameter: str
    raw_value: str | None = None
    unit: str | None = None


#: Ein Mapper bildet ein Produkt auf erlaubte ERP-Attribute ab.
Mapper = Callable[[ProviderProduct, str, AllowedAttributes], dict[str, MappedAttribute]]


def _normalize_parameter_name(name: str) -> str:
    """Vereinheitlicht einen Quellparameter-Namen für den Mapping-Vergleich."""
    return " ".join(name.strip().casefold().split())


def _normalize_unit(unit: str) -> str:
    """Vereinheitlicht ein Einheitensymbol für den Vergleich (z. B. ``Ohm``→``ohm``)."""
    stripped = unit.strip().casefold()
    return stripped.replace("ω", "ohm").replace("ohms", "ohm")


def _unit_matches_expected(expected: str | None, actual: str | None) -> bool:
    """Prüft, ob eine Quell-Einheit zur erwarteten Einheit passt.

    Ist keine erwartete Einheit definiert, gilt jede Einheit als zulässig.
    Fehlt die Quell-Einheit, kann die Eindeutigkeit nicht belegt werden – dann
    wird der Wert **nicht** als sicher gewertet (kein Vorschlag).
    """
    if expected is None:
        return True
    if actual is None:
        return False
    return _normalize_unit(expected) == _normalize_unit(actual)


@dataclass(frozen=True)
class _Candidate:
    """Ein zuordenbarer Quellwert inkl. Nachvollziehbarkeitsinformationen."""

    value: str
    source_parameter: str
    raw_value: str | None = None
    unit: str | None = None


def _candidates_from_parameters(
    parameters: Mapping[str, str],
    specs: tuple[ProviderSpec, ...],
) -> dict[str, _Candidate]:
    """Baut eine normalisierte Nachschlagetabelle aus Parametern (+ Specs)."""
    spec_by_key: dict[str, ProviderSpec] = {}
    for spec in specs:
        key = _normalize_parameter_name(spec.name)
        if key and key not in spec_by_key:
            spec_by_key[key] = spec

    candidates: dict[str, _Candidate] = {}
    for raw_name, value in parameters.items():
        key = _normalize_parameter_name(raw_name)
        if not key or key in candidates:
            continue
        matched_spec = spec_by_key.get(key)
        candidates[key] = _Candidate(
            value=value,
            source_parameter=raw_name,
            raw_value=matched_spec.raw_value if matched_spec is not None else value,
            unit=matched_spec.unit if matched_spec is not None else None,
        )
    return candidates


def map_generic_detailed(
    product: ProviderProduct,
    sachgruppe: str,
    allowed_attributes: AllowedAttributes,
) -> dict[str, MappedAttribute]:
    """Generisches Mapping (Mouser/DigiKey) mit Nachvollziehbarkeitsinformationen."""
    allowed = set(allowed_attributes)
    candidates = _candidates_from_parameters(product.parameters, product.specs)
    mapped: dict[str, MappedAttribute] = {}

    def add(attribute: str, key: str) -> None:
        candidate = candidates[key]
        mapped[attribute] = MappedAttribute(
            attribute=attribute,
            value=candidate.value,
            source_parameter=candidate.source_parameter,
            raw_value=candidate.raw_value,
            unit=candidate.unit,
        )

    if "Wert" in allowed:
        for param in SACHGRUPPE_VALUE_PARAMETERS.get(sachgruppe, ()):
            if param in candidates:
                add("Wert", param)
                break

    for param_key, attribute in COMMON_PARAMETER_MAP.items():
        if attribute in allowed and attribute not in mapped and param_key in candidates:
            add(attribute, param_key)

    return mapped


def map_parameters(
    parameters: Mapping[str, str],
    sachgruppe: str,
    allowed_attributes: AllowedAttributes,
) -> dict[str, str]:
    """Bildet Quellparameter auf erlaubte interne Attribute ab (Kurzform).

    Rückwärtskompatible Hülle um :func:`map_generic_detailed`, die nur die
    zugeordneten Werte (ohne Nachvollziehbarkeitsdetails) liefert.

    Args:
        parameters: Strukturierte Quellparameter (Name → Wert).
        sachgruppe: Sachgruppe des Artikels (steuert das ``Wert``-Mapping).
        allowed_attributes: Für die Sachgruppe laut Regelwerk erlaubte Attribute.

    Returns:
        Zuordnung interner Attributnamen zu vorgeschlagenen Werten.
    """
    product = ProviderProduct(
        manufacturer_part_number=None,
        manufacturer=None,
        parameters=dict(parameters),
    )
    detailed = map_generic_detailed(product, sachgruppe, allowed_attributes)
    return {attribute: mapped.value for attribute, mapped in detailed.items()}


@dataclass(frozen=True)
class NexarMappingRule:
    """Eine datengetriebene Mapping-Regel für Nexar-Spezifikationen.

    Attributes:
        erp_attribute: Internes ERP-Zielattribut.
        source_names: Normalisierte Nexar-Spezifikationsnamen/-Kurznamen inkl.
            Alternativbezeichnungen, die auf dieses Attribut abbilden.
        allowed_sachgruppen: Sachgruppen, für die die Regel gilt (leer = alle).
        expected_unit: Erwartete Einheit (nur zur Dokumentation/Prüfung).
        priority: Priorität bei mehreren möglichen Regeln (kleiner = höher).
    """

    erp_attribute: str
    source_names: tuple[str, ...]
    allowed_sachgruppen: frozenset[str] = frozenset()
    expected_unit: str | None = None
    priority: int = 100


@cache
def load_nexar_mapping_rules(
    path: str | None = None,
) -> tuple[NexarMappingRule, ...]:
    """Lädt die Nexar-Mapping-Regeln aus der JSON-Konfiguration (gecacht).

    Args:
        path: Optionaler Pfad zur Konfiguration (Standard:
            :data:`NEXAR_MAPPING_PATH`).

    Returns:
        Die Mapping-Regeln, nach Priorität sortiert.
    """
    if path is not None:
        raw = Path(path).read_text(encoding="utf-8")
    else:
        raw = (
            resources.files(_MAPPING_PACKAGE)
            .joinpath(NEXAR_MAPPING_FILENAME)
            .read_text(encoding="utf-8")
        )
    data = json.loads(raw)
    raw_rules = data.get("mappings", [])
    rules: list[NexarMappingRule] = []
    for entry in raw_rules:
        names: list[str] = []
        primary = entry.get("nexar_shortname")
        if isinstance(primary, str):
            names.append(primary)
        for alt in entry.get("alternative_names", []):
            if isinstance(alt, str):
                names.append(alt)
        normalized_names = tuple(
            dict.fromkeys(_normalize_parameter_name(name) for name in names if name)
        )
        allowed_raw = entry.get("allowed_sachgruppen", [])
        rules.append(
            NexarMappingRule(
                erp_attribute=str(entry["erp_attribute"]),
                source_names=normalized_names,
                allowed_sachgruppen=frozenset(
                    str(item) for item in allowed_raw if isinstance(item, str)
                ),
                expected_unit=entry.get("expected_unit"),
                priority=int(entry.get("priority", 100)),
            )
        )
    rules.sort(key=lambda rule: rule.priority)
    return tuple(rules)


def map_nexar_detailed(
    product: ProviderProduct,
    sachgruppe: str,
    allowed_attributes: AllowedAttributes,
    *,
    rules: tuple[NexarMappingRule, ...] | None = None,
) -> dict[str, MappedAttribute]:
    """Datengetriebenes Nexar-Mapping (nur strukturierte Spezifikationen).

    Args:
        product: Neutrales Produktmodell (mit ``specs`` bevorzugt genutzt).
        sachgruppe: Sachgruppe des Artikels.
        allowed_attributes: Laut Regelwerk erlaubte Attribute.
        rules: Optionale Regeln (Standard: geladen aus der JSON-Konfiguration).

    Returns:
        Zuordnung interner Attributnamen zu :class:`MappedAttribute`.
    """
    active_rules = rules if rules is not None else load_nexar_mapping_rules()
    allowed = set(allowed_attributes)

    candidates: dict[str, _Candidate] = {}
    for spec in product.specs:
        key = _normalize_parameter_name(spec.name)
        if key and key not in candidates:
            candidates[key] = _Candidate(
                value=spec.display_value,
                source_parameter=spec.name,
                raw_value=spec.raw_value,
                unit=spec.unit,
            )
    # Fallback: menschenlesbare Parameternamen (ohne getrennte Einheit).
    for raw_name, value in product.parameters.items():
        key = _normalize_parameter_name(raw_name)
        if key and key not in candidates:
            candidates[key] = _Candidate(value=value, source_parameter=raw_name)

    mapped: dict[str, MappedAttribute] = {}
    for rule in active_rules:
        if rule.erp_attribute not in allowed or rule.erp_attribute in mapped:
            continue
        if rule.allowed_sachgruppen and sachgruppe not in rule.allowed_sachgruppen:
            continue
        for name in rule.source_names:
            candidate = candidates.get(name)
            if candidate is None:
                continue
            if not _unit_matches_expected(rule.expected_unit, candidate.unit):
                # Uneindeutige/abweichende Einheit → kein sicherer Vorschlag.
                continue
            mapped[rule.erp_attribute] = MappedAttribute(
                attribute=rule.erp_attribute,
                value=candidate.value,
                source_parameter=candidate.source_parameter,
                raw_value=candidate.raw_value,
                unit=candidate.unit,
            )
            break
    return mapped


def mapper_for_provider(provider_name: str) -> Mapper:
    """Wählt den passenden Mapper anhand des Providernamens.

    Args:
        provider_name: Name des Providers (z. B. ``"mouser"``, ``"digikey-v4"``,
            ``"nexar"``).

    Returns:
        Ein :data:`Mapper`. Für Nexar wird das datengetriebene JSON-Mapping
        verwendet, sonst das generische Mapping.
    """
    if provider_name.startswith("nexar"):
        return map_nexar_detailed
    return map_generic_detailed
