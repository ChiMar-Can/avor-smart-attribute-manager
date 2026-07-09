# AVOR Smart Attribute Manager

Python-Tool zur intelligenten Pflege von ERP-Stammdaten in der Elektronikfertigung.

## Ziele

- Analyse von ERP-Exporten
- Ergänzung fehlender Attribute
- Herstellerdaten automatisch auswerten
- Vorschläge statt automatischer Änderungen
- Datenqualität bewerten

## Status

🚧 Projekt im Aufbau

## Projektübersicht

Der **AVOR Smart Attribute Manager** ist ein Windows-Desktopprogramm für die
AVOR (Arbeitsvorbereitung) einer Elektronikfertigung. Es liest
ERP-Artikelstammdaten aus Excel-Exporten ein, analysiert die Artikelattribute
und erstellt **ausschliesslich Vorschläge** zur Verbesserung der Datenqualität.

Grundregeln:

- Es werden **niemals** automatisch Änderungen am ERP vorgenommen.
- Originaldaten (ERP-Exporte) werden nur gelesen, niemals überschrieben.
- Ergebnisse werden immer in **neue** Dateien geschrieben.
- Jeder Vorschlag ist nachvollziehbar begründet.

## Projektstruktur

```
src/avor_smart_attribute_manager/   Python-Paket (modularer Code)
├── app.py            Zusammenbau/Start der Anwendung
├── config/           Konfiguration
├── models/           Gemeinsame Domänenmodelle
├── gui/              Grafische Oberfläche (PySide6)
├── excel/            Excel-Import (lesend) und -Export (neue Dateien)
├── analysis/         Attributanalyse
├── rules/            Regelprüfung
├── manufacturers/    Herstellerdaten
├── datasources/      Abstraktion externer Datenquellen
└── ai/               KI-Unterstützung (optional, gekapselt)
tests/                Automatisierte Tests
docs/                 Dokumentation (siehe docs/architecture.md)
```

Eine ausführliche Beschreibung der Architektur, der Modulverantwortlichkeiten
und der Erweiterbarkeit findet sich in
[`docs/architecture.md`](docs/architecture.md).

## Installation

Voraussetzung: **Python 3.11+**.

```bash
# Repository klonen und in das Verzeichnis wechseln
git clone https://github.com/ChiMar-Can/avor-smart-attribute-manager.git
cd avor-smart-attribute-manager

# Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Laufzeitabhängigkeiten installieren
pip install -r requirements.txt
```

Start der Anwendung (sobald implementiert):

```bash
python -m avor_smart_attribute_manager
```

> Hinweis: Das Projekt befindet sich am Anfang. Die Module sind derzeit
> dokumentierte Platzhalter; der Programmstart ist noch nicht implementiert.

## Entwicklungsumgebung

Für die Entwicklung zusätzlich die Entwicklungsabhängigkeiten installieren:

```bash
pip install -r requirements-dev.txt
# oder: pip install -e ".[dev]"
```

Qualitätswerkzeuge:

```bash
ruff check .        # Linting inkl. Import-Sortierung und Docstring-Prüfung
ruff format .       # Formatierung
mypy                # statische Typprüfung (strikt)
pytest              # Tests
```

Konfiguration der Werkzeuge liegt zentral in `pyproject.toml`.

## Roadmap

Grobe, iterative Ausbaustufen (Reihenfolge kann sich ändern):

1. **Gerüst & Werkzeuge** *(aktueller Stand)* – modulare Struktur, Platzhalter,
   Linting/Typprüfung/Tests.
2. **Domänenmodelle & Excel-Import** – Einlesen von ERP-Exporten in typisierte
   Modelle (nur lesend).
3. **Attributanalyse & Regelprüfung** – nachvollziehbare Befunde und
   Vorschläge zur Datenqualität.
4. **Excel-Export** – Ausgabe der Vorschläge in neue Dateien.
5. **GUI** – Bedienoberfläche (PySide6) zur Anzeige und Auswahl von Vorschlägen.
6. **Herstellerdaten & Datenquellen** – Abgleich über Herstellernummer;
   Anbindung externer Quellen über eine gemeinsame Schnittstelle.
7. **KI-Unterstützung** *(optional)* – klar gekapselte, optionale Vorschläge.

## Grundprinzipien

Verbindliche Prinzipien für die Weiterentwicklung sind in
[`AGENTS.md`](AGENTS.md) festgehalten.
