"""Lokaler Datei-Cache für Provider-Suchergebnisse.

Ziele:

* Dieselbe Herstellerteilenummer nicht bei jedem Lauf erneut abfragen.
* **Keine** Zugangsdaten speichern (nur Suchparameter und neutrale Ergebnisse).
* Cache nach Provider und Suchanfrage trennen.
* Zeitstempel speichern und eine konfigurierbare Gültigkeitsdauer prüfen.
* Fehlerantworten (API-Fehler/Rate-Limit) **nicht** als gültigen Treffer
  dauerhaft speichern.
* Der Cache ist jederzeit vollständig löschbar.

Der Cache liegt standardmässig unter ``.cache/`` (per ``.gitignore``
ausgeschlossen).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from avor_smart_attribute_manager.datasources.provider import (
    ProviderProduct,
    ProviderResponseStatus,
    ProviderSearchResult,
    ProviderSpec,
)

#: Standardverzeichnis des Caches (relativ zum Arbeitsverzeichnis).
DEFAULT_CACHE_DIR = Path(".cache")

#: Standard-Gültigkeitsdauer eines Cache-Eintrags in Sekunden (30 Tage).
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60


def _spec_to_dict(spec: ProviderSpec) -> dict[str, object]:
    """Serialisiert eine :class:`ProviderSpec` zu einem JSON-Objekt."""
    return {
        "name": spec.name,
        "display_value": spec.display_value,
        "raw_value": spec.raw_value,
        "unit": spec.unit,
    }


def _spec_from_dict(data: dict[str, object]) -> ProviderSpec | None:
    """Deserialisiert eine :class:`ProviderSpec` aus einem JSON-Objekt."""
    name = data.get("name")
    display_value = data.get("display_value")
    if not isinstance(name, str) or not isinstance(display_value, str):
        return None
    raw_value = data.get("raw_value")
    unit = data.get("unit")
    return ProviderSpec(
        name=name,
        display_value=display_value,
        raw_value=raw_value if isinstance(raw_value, str) else None,
        unit=unit if isinstance(unit, str) else None,
    )


def _product_to_dict(product: ProviderProduct) -> dict[str, object]:
    """Serialisiert ein :class:`ProviderProduct` zu einem JSON-Objekt."""
    return {
        "manufacturer_part_number": product.manufacturer_part_number,
        "manufacturer": product.manufacturer,
        "description": product.description,
        "category": product.category,
        "datasheet_url": product.datasheet_url,
        "product_url": product.product_url,
        "parameters": dict(product.parameters),
        "specs": [_spec_to_dict(spec) for spec in product.specs],
    }


def _product_from_dict(data: dict[str, object]) -> ProviderProduct:
    """Deserialisiert ein :class:`ProviderProduct` aus einem JSON-Objekt."""
    raw_parameters = data.get("parameters")
    parameters = (
        {str(key): str(value) for key, value in raw_parameters.items()}
        if isinstance(raw_parameters, dict)
        else {}
    )

    def _optional(field: str) -> str | None:
        value = data.get(field)
        return str(value) if isinstance(value, str) else None

    raw_specs = data.get("specs")
    specs = (
        tuple(
            spec
            for item in raw_specs
            if isinstance(item, dict)
            and (spec := _spec_from_dict(item)) is not None
        )
        if isinstance(raw_specs, list)
        else ()
    )

    return ProviderProduct(
        manufacturer_part_number=_optional("manufacturer_part_number"),
        manufacturer=_optional("manufacturer"),
        description=_optional("description"),
        category=_optional("category"),
        datasheet_url=_optional("datasheet_url"),
        product_url=_optional("product_url"),
        parameters=parameters,
        specs=specs,
    )


class SearchCache:
    """Datei-basierter Cache für :class:`ProviderSearchResult`."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Initialisiert den Cache.

        Args:
            cache_dir: Verzeichnis des Caches (Standard: :data:`DEFAULT_CACHE_DIR`).
            ttl_seconds: Gültigkeitsdauer eines Eintrags in Sekunden.
        """
        self._cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
        self._ttl_seconds = ttl_seconds

    def _entry_path(self, provider: str, mpn: str, manufacturer: str | None) -> Path:
        """Bestimmt den Dateipfad eines Cache-Eintrags (getrennt nach Provider)."""
        raw_key = f"{mpn}\x00{manufacturer or ''}"
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return self._cache_dir / provider / f"{digest}.json"

    def get(
        self, provider: str, mpn: str, manufacturer: str | None = None
    ) -> ProviderSearchResult | None:
        """Liest ein gültiges Ergebnis aus dem Cache.

        Args:
            provider: Providername.
            mpn: Bereinigte Herstellerteilenummer.
            manufacturer: Optionaler Hersteller.

        Returns:
            Das gecachte :class:`ProviderSearchResult`, wenn ein gültiger,
            nicht abgelaufener Eintrag existiert; sonst ``None``.
        """
        path = self._entry_path(provider, mpn, manufacturer)
        if not path.is_file():
            return None

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict):
            return None

        stored_at_raw = payload.get("stored_at")
        if not isinstance(stored_at_raw, str):
            return None
        try:
            stored_at = datetime.fromisoformat(stored_at_raw)
        except ValueError:
            return None

        age = (datetime.now(UTC) - stored_at).total_seconds()
        if age > self._ttl_seconds:
            return None

        result = payload.get("result")
        if not isinstance(result, dict):
            return None

        raw_products = result.get("products")
        products = (
            tuple(
                _product_from_dict(item)
                for item in raw_products
                if isinstance(item, dict)
            )
            if isinstance(raw_products, list)
            else ()
        )
        return ProviderSearchResult(
            provider=provider,
            status=ProviderResponseStatus.OK,
            products=products,
        )

    def set(
        self,
        provider: str,
        mpn: str,
        manufacturer: str | None,
        result: ProviderSearchResult,
    ) -> None:
        """Speichert ein erfolgreiches Ergebnis im Cache.

        Fehlerantworten (``API_ERROR``/``RATE_LIMITED``) werden bewusst **nicht**
        gespeichert, damit temporäre Fehler nicht dauerhaft als Treffer gelten.

        Args:
            provider: Providername.
            mpn: Bereinigte Herstellerteilenummer.
            manufacturer: Optionaler Hersteller.
            result: Das zu speichernde Ergebnis.
        """
        if result.status is not ProviderResponseStatus.OK:
            return

        path = self._entry_path(provider, mpn, manufacturer)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "provider": provider,
            "mpn": mpn,
            "manufacturer": manufacturer,
            "stored_at": datetime.now(UTC).isoformat(),
            "result": {
                "products": [_product_to_dict(p) for p in result.products],
            },
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def clear(self) -> None:
        """Löscht den gesamten Cache (Verzeichnis wird entfernt)."""
        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir)
