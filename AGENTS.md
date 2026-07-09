# AVOR Smart Attribute Manager

## Projektziel

Dieses Projekt entwickelt ein professionelles Python-Tool zur Analyse und Verbesserung von ERP-Stammdaten in einer Elektronikfertigung.

Die Software liest ERP-Excel-Exporte ein, analysiert Artikelattribute und erstellt ausschließlich Vorschläge zur Verbesserung der Datenqualität.

Originaldaten dürfen niemals automatisch verändert werden.

---

## Grundprinzipien

- Originaldaten niemals überschreiben.
- Änderungen immer als Vorschläge ausgeben.
- Jede Empfehlung muss nachvollziehbar sein.
- Bei Unsicherheit keine Vermutungen treffen.
- Code sauber dokumentieren und modular entwickeln.

---

## Technologiestack

- Python 3.11+
- PySide6
- pandas
- openpyxl

---

## Entwicklungsziel

Das Projekt soll langfristig zu einer modularen Software ausgebaut werden und nicht aus einem einzelnen Python-Skript bestehen.

---

## Projektstruktur

Der Code liegt als Python-Paket im `src`-Layout unter
`src/avor_smart_attribute_manager/`. Die Verantwortlichkeiten der Module sowie
die Erweiterbarkeit sind in `docs/architecture.md` beschrieben.

Kurzüberblick:

- `config/` – Konfiguration
- `models/` – gemeinsame Domänenmodelle
- `gui/` – Oberfläche (PySide6), nur Darstellung
- `excel/` – Import (lesend) und Export (neue Dateien)
- `analysis/` – Attributanalyse
- `rules/` – Regelprüfung
- `manufacturers/` – Herstellerdaten
- `datasources/` – Abstraktion externer Datenquellen
- `ai/` – optionale KI-Unterstützung

---

## Entwicklungsrichtlinien

- **Trennung von GUI und Businesslogik:** Die GUI ruft nur Fachmodule auf und
  stellt Ergebnisse dar. Fachlogik bleibt GUI-frei und dadurch testbar.
- **Keine unnötigen Abhängigkeiten:** Neue Abhängigkeiten nur mit klarem Nutzen;
  Abhängigkeitsrichtung gemäss `docs/architecture.md` einhalten.
- **Docstrings:** Jedes Modul und jede öffentliche Funktion/Klasse erhält einen
  aussagekräftigen Docstring (Google-Konvention).
- **Typisierung:** Neuer Code wird typisiert; `mypy` läuft strikt.
- **Sprache:** Verständliche, sprechende Datei-, Modul- und Bezeichnernamen.

---

## Qualitätswerkzeuge

Vor jedem Commit ausführen:

```bash
ruff check .        # Linting inkl. Import-Sortierung und Docstrings
mypy                # statische Typprüfung (strikt)
pytest              # Tests
```

Die Konfiguration liegt zentral in `pyproject.toml`.

---

## Arbeitsweise

- Kleine, nachvollziehbare Commits mit klaren Botschaften.
- Änderungen über Pull Requests; die PR-Beschreibung enthält Zusammenfassung,
  Begründung der Entscheidungen und nächste Schritte.
- Grössere Annahmen im Pull Request dokumentieren, nicht stillschweigend
  umsetzen.
- Keine Beispiel-ERP-Daten, keine Firmendaten und keine Geheimnisse (z. B.
  API-Schlüssel) ins Repository aufnehmen.
