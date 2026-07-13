"""Tests für die technische Normalisierung von Herstellerteilenummern."""

from __future__ import annotations

from avor_smart_attribute_manager.datasources.normalization import (
    clean_part_number,
    manufacturer_key,
    part_number_key,
)


def test_clean_part_number_strips_edges_and_invisible_chars() -> None:
    assert clean_part_number("  ABC-123  ") == "ABC-123"
    assert clean_part_number("AB\u200bC\ufeff123") == "ABC123"


def test_clean_part_number_keeps_content_suffixes() -> None:
    # Verpackungs-/Gehäuse-Suffixe dürfen NICHT abgeschnitten werden.
    assert clean_part_number("GRM188R71H104KA93D") == "GRM188R71H104KA93D"
    assert clean_part_number("LM317T/NOPB") == "LM317T/NOPB"


def test_part_number_key_is_case_insensitive_but_keeps_content() -> None:
    assert part_number_key("lm317t") == part_number_key("LM317T")
    assert part_number_key("ABC-123") != part_number_key("ABC-123-REEL")


def test_manufacturer_key_normalizes_case_and_spacing() -> None:
    assert manufacturer_key("  Texas   Instruments ") == manufacturer_key(
        "texas instruments"
    )
    assert manufacturer_key("Murata") != manufacturer_key("Yageo")
