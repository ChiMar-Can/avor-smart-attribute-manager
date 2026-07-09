"""Laden und Repräsentation des Sachgruppen-/Attribut-Regelwerks.

Das Regelwerk legt je Sachgruppenklasse fest, welche Attribute erlaubt bzw.
relevant sind. Es wird bewusst **nicht** hart im Code hinterlegt, sondern aus
einer Konfigurationsdatei (Standard: ``config/attribute_rules.json`` im Paket)
geladen, damit es ohne Codeänderung erweitert werden kann.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

#: Ressourcenpaket, in dem das mitgelieferte Standard-Regelwerk liegt.
_DEFAULT_RULES_PACKAGE = "avor_smart_attribute_manager.config"

#: Dateiname des mitgelieferten Standard-Regelwerks.
_DEFAULT_RULES_FILENAME = "attribute_rules.json"

#: Sachgruppe, deren Attribute als globale Attribute gelten. Sie ist selbst
#: **keine** eigenständige Sachgruppe, sondern wird beim Laden automatisch mit
#: jeder anderen Sachgruppe zusammengeführt (globale Attribute zuerst).
GLOBAL_SACHGRUPPE = "Allgemein"


class InvalidRulesError(ValueError):
    """Wird ausgelöst, wenn die Regelwerksdatei strukturell ungültig ist."""


@dataclass(frozen=True)
class AttributeRules:
    """Repräsentiert das geladene Regelwerk.

    Attributes:
        rules_by_sachgruppe: Zuordnung von Sachgruppenklasse zu den erlaubten/
            relevanten Attributnamen in definierter Reihenfolge (globale
            Attribute zuerst). Duplikate sind bereits entfernt.
    """

    rules_by_sachgruppe: Mapping[str, tuple[str, ...]]

    def is_known(self, sachgruppe: str) -> bool:
        """Prüft, ob eine Sachgruppenklasse im Regelwerk hinterlegt ist.

        Args:
            sachgruppe: Zu prüfende Sachgruppenklasse.

        Returns:
            ``True``, wenn die Sachgruppe bekannt ist, sonst ``False``.
        """
        return sachgruppe in self.rules_by_sachgruppe

    def allowed_for(self, sachgruppe: str) -> tuple[str, ...]:
        """Liefert die erlaubten Attribute einer Sachgruppenklasse.

        Die globalen Attribute (Sachgruppe ``Allgemein``) sind bereits
        eingemischt und stehen – unter Beibehaltung der Reihenfolge – vor den
        sachgruppenspezifischen Attributen.

        Args:
            sachgruppe: Sachgruppenklasse, deren erlaubte Attribute gesucht
                werden.

        Returns:
            Die erlaubten Attributnamen in definierter Reihenfolge; ein leeres
            Tupel, wenn die Sachgruppe unbekannt ist.
        """
        return self.rules_by_sachgruppe.get(sachgruppe, ())

    @property
    def known_sachgruppen(self) -> frozenset[str]:
        """Alle im Regelwerk hinterlegten Sachgruppenklassen."""
        return frozenset(self.rules_by_sachgruppe)


#: Standardbeschreibung des generierten Regelwerks.
_GENERATED_DESCRIPTION = (
    "Automatisch aus dem Attribut-Katalog generiert. Nicht manuell bearbeiten – "
    "stattdessen den Katalog pflegen und neu generieren (siehe README)."
)


def rules_document_from_mapping(
    mapping: Mapping[str, list[str]],
    *,
    version: int = 1,
    description: str = _GENERATED_DESCRIPTION,
) -> dict[str, object]:
    """Erzeugt das JSON-Dokument des Regelwerks aus einer Zuordnung.

    Args:
        mapping: Zuordnung von Sachgruppenklasse zu erlaubten Attributnamen.
        version: Schemaversion des Regelwerks.
        description: In das Dokument geschriebene Beschreibung.

    Returns:
        Ein serialisierbares Dictionary im Schema der Regelwerksdatei.
    """
    sachgruppen = {
        sachgruppe: {"allowed_attributes": list(attributes)}
        for sachgruppe, attributes in mapping.items()
    }
    return {
        "version": version,
        "description": description,
        "sachgruppen": sachgruppen,
    }


def _dedupe_preserving_order(items: Iterable[str]) -> tuple[str, ...]:
    """Entfernt Duplikate und behält die Reihenfolge des ersten Auftretens bei."""
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return tuple(seen)


def _parse_rules(data: object) -> AttributeRules:
    """Wandelt die geladenen JSON-Daten in :class:`AttributeRules` um.

    Die Attribute der Sachgruppe ``Allgemein`` (siehe :data:`GLOBAL_SACHGRUPPE`)
    gelten global: Sie werden jeder anderen Sachgruppe vorangestellt und
    dedupliziert; ``Allgemein`` selbst wird **nicht** als eigenständige
    Sachgruppe geführt.

    Args:
        data: Bereits deserialisierter Inhalt der Regelwerksdatei.

    Returns:
        Das validierte Regelwerk.

    Raises:
        InvalidRulesError: Wenn die Struktur nicht dem erwarteten Schema
            entspricht.
    """
    if not isinstance(data, dict):
        raise InvalidRulesError("Regelwerk muss ein JSON-Objekt sein.")

    sachgruppen = data.get("sachgruppen")
    if not isinstance(sachgruppen, dict):
        raise InvalidRulesError("Feld 'sachgruppen' muss ein JSON-Objekt sein.")

    parsed: dict[str, tuple[str, ...]] = {}
    for sachgruppe, definition in sachgruppen.items():
        if not isinstance(definition, dict):
            raise InvalidRulesError(
                f"Definition der Sachgruppe '{sachgruppe}' muss ein Objekt sein."
            )
        allowed = definition.get("allowed_attributes")
        if not isinstance(allowed, list) or not all(
            isinstance(item, str) for item in allowed
        ):
            raise InvalidRulesError(
                f"'allowed_attributes' der Sachgruppe '{sachgruppe}' muss eine "
                "Liste von Zeichenketten sein."
            )
        parsed[sachgruppe] = tuple(allowed)

    global_attributes = parsed.pop(GLOBAL_SACHGRUPPE, ())
    rules = {
        sachgruppe: _dedupe_preserving_order((*global_attributes, *specific))
        for sachgruppe, specific in parsed.items()
    }

    return AttributeRules(rules_by_sachgruppe=rules)


def load_attribute_rules(path: Path | None = None) -> AttributeRules:
    """Lädt das Regelwerk aus einer JSON-Datei.

    Args:
        path: Optionaler Pfad zu einer Regelwerksdatei. Ohne Angabe wird das im
            Paket mitgelieferte Standard-Regelwerk geladen.

    Returns:
        Das validierte Regelwerk.

    Raises:
        InvalidRulesError: Wenn die Datei kein gültiges JSON enthält oder nicht
            dem erwarteten Schema entspricht.
    """
    if path is None:
        source = resources.files(_DEFAULT_RULES_PACKAGE).joinpath(
            _DEFAULT_RULES_FILENAME
        )
        raw = source.read_text(encoding="utf-8")
    else:
        raw = Path(path).read_text(encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise InvalidRulesError(f"Regelwerk ist kein gültiges JSON: {error}") from error

    return _parse_rules(data)
