"""Anwendungseinstellungen (typisiert, aus Umgebung/.env geladen).

Grundsätze:

* Eine zentrale, klar typisierte Einstellungsstruktur (:class:`Settings`).
* Standardwerte im Code, Überschreibungen aus der Umgebung bzw. einer lokalen,
  **nicht versionierten** ``.env``-Datei.
* Geheimnisse (z. B. ``MOUSER_API_KEY``) werden **niemals** im Code oder
  Repository hinterlegt, sondern ausschliesslich über Umgebungsvariablen
  bereitgestellt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from avor_smart_attribute_manager.datasources.cache import (
    DEFAULT_CACHE_DIR,
    DEFAULT_TTL_SECONDS,
)
from avor_smart_attribute_manager.datasources.mouser import (
    API_KEY_ENV_VAR,
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
)


@dataclass(frozen=True)
class Settings:
    """Typisierte Anwendungseinstellungen.

    Attributes:
        mouser_api_key: API-Schlüssel für Mouser (``None``, wenn nicht gesetzt).
        request_timeout: Timeout je API-Anfrage in Sekunden.
        max_retries: Zusätzliche Wiederholungen bei temporären Fehlern.
        backoff_seconds: Basiswert für exponentiellen Backoff.
        cache_dir: Verzeichnis des lokalen Suchergebnis-Caches.
        cache_ttl_seconds: Gültigkeitsdauer eines Cache-Eintrags in Sekunden.
        use_cache: Ob der lokale Cache genutzt werden soll.
    """

    mouser_api_key: str | None = None
    request_timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS
    cache_dir: Path = DEFAULT_CACHE_DIR
    cache_ttl_seconds: int = DEFAULT_TTL_SECONDS
    use_cache: bool = True


def parse_dotenv(text: str) -> dict[str, str]:
    """Liest ``KEY=VALUE``-Paare aus dem Inhalt einer ``.env``-Datei.

    Unterstützt Kommentarzeilen (``#``), leere Zeilen und optionale
    Anführungszeichen um Werte. Bewusst minimal gehalten (keine zusätzliche
    Abhängigkeit).

    Args:
        text: Inhalt der ``.env``-Datei.

    Returns:
        Zuordnung der gefundenen Schlüssel zu Werten.
    """
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _read_environment(dotenv_path: Path | None) -> dict[str, str]:
    """Führt ``.env`` und Prozessumgebung zusammen (Umgebung hat Vorrang)."""
    dotenv_values: dict[str, str] = {}
    path = dotenv_path if dotenv_path is not None else Path(".env")
    if path.is_file():
        dotenv_values = parse_dotenv(path.read_text(encoding="utf-8"))
    return {**dotenv_values, **os.environ}


def _get_float(env: dict[str, str], key: str, default: float) -> float:
    """Liest einen Float-Wert aus der Umgebung (Fallback bei Fehler)."""
    try:
        return float(env[key])
    except (KeyError, ValueError):
        return default


def _get_int(env: dict[str, str], key: str, default: int) -> int:
    """Liest einen Int-Wert aus der Umgebung (Fallback bei Fehler)."""
    try:
        return int(env[key])
    except (KeyError, ValueError):
        return default


def load_settings(dotenv_path: Path | None = None) -> Settings:
    """Lädt die Anwendungseinstellungen aus Umgebung und optionaler ``.env``.

    Args:
        dotenv_path: Optionaler Pfad zu einer ``.env``-Datei (Standard: ``.env``
            im Arbeitsverzeichnis, falls vorhanden).

    Returns:
        Die geladenen :class:`Settings`.
    """
    env = _read_environment(dotenv_path)
    api_key = env.get(API_KEY_ENV_VAR, "").strip() or None
    cache_dir_raw = env.get("AVOR_CACHE_DIR", "").strip()

    return Settings(
        mouser_api_key=api_key,
        request_timeout=_get_float(env, "AVOR_REQUEST_TIMEOUT", DEFAULT_TIMEOUT_SECONDS),
        max_retries=_get_int(env, "AVOR_MAX_RETRIES", DEFAULT_MAX_RETRIES),
        backoff_seconds=_get_float(
            env, "AVOR_BACKOFF_SECONDS", DEFAULT_BACKOFF_SECONDS
        ),
        cache_dir=Path(cache_dir_raw) if cache_dir_raw else DEFAULT_CACHE_DIR,
        cache_ttl_seconds=_get_int(env, "AVOR_CACHE_TTL_SECONDS", DEFAULT_TTL_SECONDS),
        use_cache=env.get("AVOR_USE_CACHE", "1").strip().lower()
        not in {"0", "false", "no"},
    )
