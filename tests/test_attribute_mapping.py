"""Tests für das sachgruppenabhängige Attribut-Mapping."""

from __future__ import annotations

from avor_smart_attribute_manager.analysis.attribute_mapping import map_parameters


def test_maps_only_allowed_attributes() -> None:
    parameters = {"Tolerance": "1%", "Voltage Rating": "50V"}
    mapped = map_parameters(parameters, "Widerstand", allowed_attributes={"Toleranz"})

    assert mapped == {"Toleranz": "1%"}
    assert "Spannung" not in mapped


def test_value_is_sachgruppe_dependent() -> None:
    resistor = map_parameters(
        {"Resistance": "10k"}, "Widerstand", {"Wert"}
    )
    capacitor = map_parameters(
        {"Capacitance": "100nF"}, "Kondensator", {"Wert"}
    )

    assert resistor == {"Wert": "10k"}
    assert capacitor == {"Wert": "100nF"}


def test_wrong_value_parameter_is_ignored() -> None:
    # Kapazität ist für Widerstand kein Wert-Parameter → nicht raten.
    mapped = map_parameters({"Capacitance": "100nF"}, "Widerstand", {"Wert"})
    assert mapped == {}


def test_unknown_parameters_are_not_guessed() -> None:
    mapped = map_parameters(
        {"Some Weird Attribute": "x"},
        "Widerstand",
        {"Wert", "Toleranz", "Spannung"},
    )
    assert mapped == {}


def test_parameter_names_are_case_insensitive() -> None:
    mapped = map_parameters({"tolerance": "5%"}, "Widerstand", {"Toleranz"})
    assert mapped == {"Toleranz": "5%"}
