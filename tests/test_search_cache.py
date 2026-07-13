"""Tests für den lokalen Datei-Cache."""

from __future__ import annotations

from pathlib import Path

from avor_smart_attribute_manager.datasources.cache import SearchCache
from avor_smart_attribute_manager.datasources.provider import (
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
)


def _ok_result() -> ProviderSearchResult:
    return ProviderSearchResult(
        provider="mouser",
        status=ProviderResponseStatus.OK,
        products=(
            ProviderProduct(
                manufacturer_part_number="LM317T",
                manufacturer="Texas Instruments",
                parameters={"Tolerance": "1%"},
            ),
        ),
    )


def test_set_and_get_roundtrip(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    cache.set("mouser", "LM317T", "Texas Instruments", _ok_result())

    cached = cache.get("mouser", "LM317T", "Texas Instruments")

    assert cached is not None
    assert cached.status is ProviderResponseStatus.OK
    assert cached.products[0].manufacturer_part_number == "LM317T"
    assert cached.products[0].parameters == {"Tolerance": "1%"}


def test_get_miss_returns_none(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    assert cache.get("mouser", "UNKNOWN") is None


def test_ttl_expiry(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path, ttl_seconds=0)
    cache.set("mouser", "LM317T", None, _ok_result())
    # Mit TTL 0 ist der Eintrag sofort abgelaufen.
    assert cache.get("mouser", "LM317T", None) is None


def test_error_results_are_not_cached(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    for status in (ProviderResponseStatus.API_ERROR, ProviderResponseStatus.RATE_LIMITED):
        cache.set(
            "mouser",
            "LM317T",
            None,
            ProviderSearchResult(provider="mouser", status=status),
        )
    assert cache.get("mouser", "LM317T", None) is None


def test_provider_separation(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    cache.set("mouser", "LM317T", None, _ok_result())
    assert cache.get("digikey", "LM317T", None) is None


def test_no_api_key_persisted(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    cache.set("mouser", "LM317T", None, _ok_result())
    contents = "\n".join(p.read_text() for p in tmp_path.rglob("*.json"))
    assert "apikey" not in contents.lower()


def test_clear_removes_cache(tmp_path: Path) -> None:
    cache = SearchCache(tmp_path)
    cache.set("mouser", "LM317T", None, _ok_result())
    cache.clear()
    assert cache.get("mouser", "LM317T", None) is None
    assert not (tmp_path).exists()
