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

## Datenqualitätsprüfung (Excel-Import & Regelwerk)

Der erste fachliche Baustein ist umgesetzt: ERP-Excel-Exporte einlesen und je
Artikel anhand der `SACHGRUPPENKLASSE` prüfen, welche Attribute relevant bzw.
erlaubt sind. Es werden **ausschliesslich Prüfergebnisse** erzeugt – keine
ERP-Werte verändert.

Ablauf in Kürze:

```python
from avor_smart_attribute_manager.analysis import analyze_workbook

results = analyze_workbook("erp_export.xlsx")  # nur lesend
for result in results:
    print(result.article_number, result.status, result.missing_attributes)
```

- **Import:** validiert die Basisspalten (`ARTIKELNUMMER`,
  `SACHGRUPPENKLASSE`) und normalisiert Attribut-Spaltennamen
  (z. B. `Dimmension` → `Dimension`, `SMD-Bauform` → `SmdBauform`).
- **Regelwerk:** je Sachgruppe erlaubte Attribute; **generiert** nach
  `src/avor_smart_attribute_manager/config/attribute_rules.json` (nicht im Code
  und nicht von Hand gepflegt).
- **Ergebnis:** je Artikel Status (`OK`, `UNKNOWN_SACHGRUPPE`, `ISSUES_FOUND`)
  sowie fehlende bzw. unzulässig gefüllte Attribute.

### Attributregeln pflegen

Die Sachgruppen und ihre erlaubten Attribute werden fachlich in einer
Excel-Liste gepflegt: `data/attribute_catalog/20260706_Attribute.xlsx`
(Spalten `Sachgruppe`, `Attribut`). Daraus wird das Regelwerk generiert:

```bash
python scripts/generate_attribute_rules.py
```

Neue Sachgruppe oder neues Attribut: Zeile(n) im Katalog ergänzen, ggf. eine
Spalten-Normalisierung in `excel/columns.py` hinzufügen, dann neu generieren.

Die Sachgruppe **`Allgemein`** ist keine eigenständige Sachgruppe, sondern
definiert globale Attribute: Beim Laden werden sie automatisch jeder anderen
Sachgruppe vorangestellt (Duplikate entfernt, Reihenfolge beibehalten).

Details zu Schema und Ablauf: [`docs/architecture.md`](docs/architecture.md).

## Roadmap

Grobe, iterative Ausbaustufen (Reihenfolge kann sich ändern):

1. **Gerüst & Werkzeuge** *(erledigt)* – modulare Struktur,
   Linting/Typprüfung/Tests.
2. **Domänenmodelle & Excel-Import** *(erledigt)* – Einlesen von ERP-Exporten
   in typisierte Modelle (nur lesend), Spaltennormalisierung.
3. **Regelwerk & Regelprüfung** *(erledigt)* – Sachgruppen-Regelwerk und
   nachvollziehbare Prüfergebnisse zur Datenqualität.
4. **Excel-Export** – Ausgabe der Prüfergebnisse/Vorschläge in neue Dateien.
5. **GUI** – Bedienoberfläche (PySide6) zur Anzeige und Auswahl von Vorschlägen.
6. **Herstellerdaten & Datenquellen** – Abgleich über Herstellernummer;
   Anbindung externer Quellen über eine gemeinsame Schnittstelle.
7. **KI-Unterstützung** *(optional)* – klar gekapselte, optionale Vorschläge.

## Grundprinzipien

Verbindliche Prinzipien für die Weiterentwicklung sind in
[`AGENTS.md`](AGENTS.md) festgehalten.
