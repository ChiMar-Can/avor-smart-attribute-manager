"""Tests für das datengetriebene Nexar-Attribut-Mapping.

Es wird ausschliesslich mit strukturierten Spezifikationen gearbeitet; Freitext
(Beschreibung/Benennung) darf niemals einen Vorschlag erzeugen. Mehrdeutige oder
abweichende Einheiten führen bewusst zu **keinem** Vorschlag.
"""

from __future__ import annotations

from avor_smart_attribute_manager.analysis.attribute_mapping import (
    NexarMappingRule,
    load_nexar_mapping_rules,
    map_nexar_detailed,
)
from avor_smart_attribute_manager.datasources.provider import (
    ProviderProduct,
    ProviderSpec,
)


def _product(*specs: ProviderSpec, description: str | None = None) -> ProviderProduct:
    return ProviderProduct(
        manufacturer_part_number="RC0805FR-071KL",
        manufacturer="Yageo",
        description=description,
        specs=specs,
    )


def test_config_loads_rules() -> None:
    rules = load_nexar_mapping_rules()
    assert rules  # Konfiguration ist nicht leer
    assert any(rule.erp_attribute == "Wert" for rule in rules)
    # Nach Priorität sortiert (aufsteigend).
    priorities = [rule.priority for rule in rules]
    assert priorities == sorted(priorities)


def test_structured_resistance_maps_to_wert() -> None:
    product = _product(
        ProviderSpec(
            name="resistance", display_value="1 kΩ", raw_value="1000", unit="Ω"
        )
    )
    mapped = map_nexar_detailed(product, "Widerstand", ("Wert",))

    assert "Wert" in mapped
    assert mapped["Wert"].value == "1 kΩ"
    assert mapped["Wert"].raw_value == "1000"
    assert mapped["Wert"].unit == "Ω"
    assert mapped["Wert"].source_parameter == "resistance"


def test_only_allowed_attributes_are_mapped() -> None:
    product = _product(
        ProviderSpec(name="resistance", display_value="1 kΩ", unit="Ω"),
        ProviderSpec(name="tolerance", display_value="1%", unit="%"),
    )
    # Nur "Wert" erlaubt → Toleranz wird nicht vorgeschlagen.
    mapped = map_nexar_detailed(product, "Widerstand", ("Wert",))

    assert set(mapped) == {"Wert"}


def test_sachgruppe_filter_blocks_rule() -> None:
    product = _product(
        ProviderSpec(name="resistance", display_value="1 kΩ", unit="Ω")
    )
    # resistance-Regel gilt nur für "Widerstand"; hier andere Sachgruppe.
    mapped = map_nexar_detailed(product, "Kondensator", ("Wert",))

    assert "Wert" not in mapped


def test_ambiguous_unit_blocks_suggestion() -> None:
    # Erwartet Ω, geliefert wird V → kein Vorschlag.
    rules = (
        NexarMappingRule(
            erp_attribute="Wert",
            source_names=("resistance",),
            expected_unit="Ω",
        ),
    )
    product = _product(
        ProviderSpec(name="resistance", display_value="5", unit="V")
    )
    mapped = map_nexar_detailed(product, "Widerstand", ("Wert",), rules=rules)

    assert mapped == {}


def test_missing_unit_blocks_when_unit_expected() -> None:
    rules = (
        NexarMappingRule(
            erp_attribute="Wert",
            source_names=("resistance",),
            expected_unit="Ω",
        ),
    )
    product = _product(
        ProviderSpec(name="resistance", display_value="1000", unit=None)
    )
    mapped = map_nexar_detailed(product, "Widerstand", ("Wert",), rules=rules)

    assert mapped == {}


def test_unit_normalization_accepts_equivalents() -> None:
    rules = (
        NexarMappingRule(
            erp_attribute="Wert",
            source_names=("resistance",),
            expected_unit="Ω",
        ),
    )
    # "Ohm" bzw. "ohms" gelten als äquivalent zu "Ω".
    product = _product(
        ProviderSpec(name="resistance", display_value="1 kOhm", unit="Ohm")
    )
    mapped = map_nexar_detailed(product, "Widerstand", ("Wert",), rules=rules)

    assert mapped["Wert"].value == "1 kOhm"


def test_no_expected_unit_allows_any() -> None:
    rules = (
        NexarMappingRule(
            erp_attribute="Bauform",
            source_names=("casepackage",),
            expected_unit=None,
        ),
    )
    product = _product(
        ProviderSpec(name="casepackage", display_value="0805", unit=None)
    )
    mapped = map_nexar_detailed(product, "Widerstand", ("Bauform",), rules=rules)

    assert mapped["Bauform"].value == "0805"


def test_priority_and_alternatives_pick_first_available() -> None:
    rules = (
        NexarMappingRule(
            erp_attribute="Spannung",
            source_names=("voltagerating", "voltage"),
            expected_unit="V",
            priority=10,
        ),
    )
    product = _product(
        ProviderSpec(name="voltage", display_value="50 V", unit="V")
    )
    mapped = map_nexar_detailed(product, "Kondensator", ("Spannung",), rules=rules)

    assert mapped["Spannung"].value == "50 V"


def test_description_is_never_used_as_source() -> None:
    # Nur Freitext, keine strukturierte Spezifikation → kein Vorschlag.
    product = _product(description="RES 1K OHM 1% 0805 resistance 1kOhm")
    mapped = map_nexar_detailed(
        product, "Widerstand", ("Wert", "Toleranz", "Bauform")
    )

    assert mapped == {}
