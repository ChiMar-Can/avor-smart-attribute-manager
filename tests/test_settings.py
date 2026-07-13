"""Tests für das Laden der Anwendungseinstellungen."""

from __future__ import annotations

from pathlib import Path

import pytest

from avor_smart_attribute_manager.config.settings import load_settings, parse_dotenv


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
