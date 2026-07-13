"""Tests für das Laden der Anwendungseinstellungen."""

from __future__ import annotations

from pathlib import Path

import pytest

from avor_smart_attribute_manager.config.settings import (
    DIGIKEY_PROVIDER,
    MOUSER_PROVIDER,
    load_settings,
    parse_dotenv,
)
from avor_smart_attribute_manager.datasources.digikey import DigiKeyApiVersion


def test_parse_dotenv_handles_comments_and_quotes() -> None:
    text = "\n".join(
        [
            "# Kommentar",
            "",
            "MOUSER_API_KEY='geheim'",
            'AVOR_MAX_RETRIES="3"',
        ]
    )
    parsed = parse_dotenv(text)
    assert parsed["MOUSER_API_KEY"] == "geheim"
    assert parsed["AVOR_MAX_RETRIES"] == "3"


def test_load_settings_from_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("MOUSER_API_KEY=from_dotenv\n", encoding="utf-8")

    settings = load_settings(dotenv)
    assert settings.mouser_api_key == "from_dotenv"


def test_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("MOUSER_API_KEY=from_dotenv\n", encoding="utf-8")
    monkeypatch.setenv("MOUSER_API_KEY", "from_env")

    settings = load_settings(dotenv)
    assert settings.mouser_api_key == "from_env"


def test_missing_key_is_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOUSER_API_KEY", raising=False)
    settings = load_settings(tmp_path / "missing.env")
    assert settings.mouser_api_key is None


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "AVOR_PROVIDER",
        "DIGIKEY_CLIENT_ID",
        "DIGIKEY_CLIENT_SECRET",
        "DIGIKEY_API_VERSION",
        "DIGIKEY_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_provider_is_mouser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clean_env(monkeypatch)
    settings = load_settings(tmp_path / "missing.env")
    assert settings.provider == MOUSER_PROVIDER
    assert settings.digikey_api_version is DigiKeyApiVersion.V4


def test_digikey_settings_from_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clean_env(monkeypatch)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "AVOR_PROVIDER=digikey",
                "DIGIKEY_CLIENT_ID=id123",
                "DIGIKEY_CLIENT_SECRET=secret123",
                "DIGIKEY_API_VERSION=v3",
                "DIGIKEY_BASE_URL=https://sandbox-api.digikey.com",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(dotenv)
    assert settings.provider == DIGIKEY_PROVIDER
    assert settings.digikey_client_id == "id123"
    assert settings.digikey_client_secret == "secret123"
    assert settings.digikey_api_version is DigiKeyApiVersion.V3
    assert settings.digikey_base_url == "https://sandbox-api.digikey.com"


def test_invalid_provider_falls_back_to_mouser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clean_env(monkeypatch)
    dotenv = tmp_path / ".env"
    dotenv.write_text("AVOR_PROVIDER=unbekannt\n", encoding="utf-8")

    settings = load_settings(dotenv)
    assert settings.provider == MOUSER_PROVIDER


def test_invalid_digikey_version_falls_back_to_v4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clean_env(monkeypatch)
    dotenv = tmp_path / ".env"
    dotenv.write_text("DIGIKEY_API_VERSION=v9\n", encoding="utf-8")

    settings = load_settings(dotenv)
    assert settings.digikey_api_version is DigiKeyApiVersion.V4
