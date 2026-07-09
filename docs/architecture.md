# Architektur

Dieses Dokument beschreibt die Struktur des **AVOR Smart Attribute Manager**,
begründet die Designentscheidungen und erklärt, wie neue Module später
integriert werden.

> Hinweis: Das Projekt befindet sich am Anfang. Sämtliche Module sind derzeit
> dokumentierte **Platzhalter** ohne Geschäftslogik. Dieses Dokument legt den
> Rahmen fest, in den die spätere Implementierung eingefügt wird.

## Leitprinzipien

Die Architektur folgt den in `AGENTS.md` festgehaltenen Grundprinzipien:

- **Nur Vorschläge:** Die Software erzeugt ausschliesslich Verbesserungs-
  vorschläge. Es werden niemals automatisch Änderungen am ERP vorgenommen.
- **Originaldaten sind unantastbar:** ERP-Exporte werden ausschliesslich
  gelesen. Ergebnisse werden immer in neue Dateien geschrieben.
- **Nachvollziehbarkeit:** Jeder Befund und jeder Vorschlag muss begründbar
  sein.
- **Trennung von GUI und Businesslogik:** Die Oberfläche stellt nur dar und
  leitet Aktionen weiter; die Fachlogik ist unabhängig von der GUI testbar.
- **Modularität und Erweiterbarkeit:** Klar abgegrenzte Module mit definierten
  Verantwortlichkeiten; neue Funktionen lassen sich ergänzen, ohne bestehenden
  Code umzubauen.

## Projektstruktur (`src`-Layout)

Das Projekt verwendet ein `src`-Layout. Dadurch wird das installierte Paket
sauber vom Projekt-Wurzelverzeichnis getrennt, versehentliche Importe aus dem
Arbeitsverzeichnis werden vermieden, und Tests laufen gegen das tatsächlich
installierte Paket.

```
avor-smart-attribute-manager/
├── src/
│   └── avor_smart_attribute_manager/   # Python-Paket (importierbarer Code)
│       ├── __init__.py                 # Paketmetadaten (Version)
│       ├── __main__.py                 # Einstiegspunkt: python -m ...
│       ├── app.py                      # Bootstrap / Zusammenbau der Bausteine
│       ├── config/                     # Konfiguration
│       │   ├── __init__.py
│       │   └── settings.py
│       ├── models/                     # Gemeinsame Domänenmodelle
│       │   ├── __init__.py
│       │   └── article.py
│       ├── gui/                        # Präsentationsschicht (PySide6)
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   └── views/
│       │       └── __init__.py
│       ├── excel/                      # Excel-Import und -Export
│       │   ├── __init__.py
│       │   ├── importer.py             # Nur lesend
│       │   └── exporter.py             # Schreibt nur neue Dateien
│       ├── analysis/                   # Attributanalyse
│       │   ├── __init__.py
│       │   └── attribute_analyzer.py
│       ├── rules/                      # Regelprüfung
│       │   ├── __init__.py
│       │   └── rule_engine.py
│       ├── manufacturers/              # Herstellerdaten
│       │   ├── __init__.py
│       │   └── manufacturer_data.py
│       ├── datasources/                # Abstraktion externer Datenquellen
│       │   ├── __init__.py
│       │   └── base.py
│       └── ai/                         # KI-Unterstützung (optional, gekapselt)
│           ├── __init__.py
│           └── suggestions.py
├── tests/                              # Automatisierte Tests
├── docs/                               # Dokumentation (dieses Dokument)
├── pyproject.toml                      # Packaging + Werkzeugkonfiguration
├── requirements.txt                    # Laufzeitabhängigkeiten
├── requirements-dev.txt                # Entwicklungsabhängigkeiten
└── README.md
```

## Verantwortung der Module

| Modul | Verantwortung |
| --- | --- |
| `config` | Zentrale Anwendungseinstellungen; trennt Standardwerte von umgebungsspezifischen Werten. Keine Geheimnisse im Code. |
| `models` | Technologie-neutrale Domänenobjekte (Artikel, Attribut, Vorschlag). Gemeinsames Vokabular aller Module. |
| `gui` | Präsentationsschicht auf Basis von PySide6. Reine Darstellung und Weiterleitung von Benutzeraktionen – **keine** Businesslogik. |
| `excel.importer` | Einlesen von ERP-Excel-Exporten. Arbeitet **ausschliesslich lesend**. |
| `excel.exporter` | Schreiben von Vorschlägen/Ergebnissen in **neue** Excel-Dateien. Verändert nie das Original. |
| `analysis` | Attributanalyse zur Bewertung der Datenqualität; erzeugt nachvollziehbare Befunde und Vorschläge. |
| `rules` | Prüfung der Daten gegen konfigurierbare Regeln; erzeugt nachvollziehbare Regelverstösse als Vorschläge. |
| `manufacturers` | Herstellerspezifische Aufbereitung/Abgleich (z. B. über Herstellernummer). Aktuell ohne externe Anbindung. |
| `datasources` | Einheitliche Schnittstelle für externe Datenquellen. Entkoppelt Fachmodule von konkreten Quellen. |
| `ai` | Optionale, klar gekapselte KI-Unterstützung für Vorschläge. Aktuell nicht implementiert. |
| `tests` | Automatisierte Tests; spiegeln die Paketstruktur wider. |

## Datenfluss

Der Ablauf verdeutlicht das Zusammenspiel der Module. Die Schritte
**Import**, **Regelwerk** und **Regelprüfung** sind implementiert; die übrigen
sind vorgesehen:

```
ERP-Excel-Export (nur lesen)
        │
        ▼
   excel.importer  ──►  models.Article  ◄────────┐   [implementiert]
        │                                         │
        ▼                                         │
   rules (Regelwerk + Regelprüfung)              │   [implementiert]
   analysis.attribute_analyzer (Orchestrierung)  │   [implementiert]
        │                                         │
        │   (optional, später)                    │
        ▼                                         │
   manufacturers ──► datasources                  │
        │                                         │
        ▼                                         │
   ai (optional, nur Vorschläge)                  │
        │                                         │
        ▼                                         │
   models.ArticleValidationResult ───────────────┘
        │
        ├──►  gui   (Anzeige, Auswahl)            [später]
        └──►  excel.exporter  ──►  NEUE Excel-Datei [später]
```

Die GUI ruft die Fachmodule auf und stellt deren Ergebnisse dar. Die
Fachmodule kennen die GUI nicht und sind dadurch unabhängig testbar.

## Import und Regelprüfung (aktueller Funktionsstand)

### Excel-Import

`excel.importer` liest ERP-Exporte **ausschliesslich lesend** ein
(`read_workbook`), normalisiert die Spaltennamen (`normalize_dataframe`) und
überführt die Zeilen in `models.Article` (`to_articles`). `load_articles`
bündelt diese Schritte.

- **Basisspalten:** `ARTIKELNUMMER` und `SACHGRUPPENKLASSE` müssen vorhanden
  sein, sonst wird `MissingBaseColumnsError` ausgelöst.
- **Spaltennormalisierung:** Nur die in
  `excel.columns.COLUMN_RENAME_MAP` hinterlegten Attributspalten werden
  umbenannt (z. B. `Dimmension` → `Dimension`, `SMD-Bauform` → `SmdBauform`).
  Basisspalten bleiben unverändert.
- **Leere Werte** (`None`, `NaN`, leere/whitespace-Strings) werden zu `None`
  vereinheitlicht, damit nachgelagerte Prüfungen ohne pandas-Kenntnis
  auskommen.

### Regelwerk

Das Regelwerk legt je `SACHGRUPPENKLASSE` fest, welche Attribute erlaubt bzw.
relevant sind. Es steht **nicht** hart im Code, sondern in einer
Konfigurationsdatei und wird über `rules.load_attribute_rules` geladen.

- **Ort der Regeln:** `src/avor_smart_attribute_manager/config/attribute_rules.json`
  (als Paketdaten mitgeliefert). Alternativ kann `load_attribute_rules(path)`
  eine externe Datei laden.
- **Schema:**

  ```json
  {
    "version": 1,
    "sachgruppen": {
      "<SACHGRUPPENKLASSE>": {
        "allowed_attributes": ["<AttributName>", "..."]
      }
    }
  }
  ```

  Beispiel (nur zur Veranschaulichung, keine realen Firmendaten):

  ```json
  {
    "version": 1,
    "sachgruppen": {
      "WIDERSTAND": { "allowed_attributes": ["Dimension", "Widerstandattribut"] }
    }
  }
  ```

- **Attributnamen** entsprechen den **normalisierten** Spaltennamen (siehe
  `COLUMN_RENAME_MAP`).
- Das mitgelieferte Regelwerk wird **aus dem Attribut-Katalog generiert** (siehe
  unten) und enthält die realen Sachgruppen. Es wird **nicht** von Hand
  gepflegt.

### Attribut-Katalog und Generierung

Die Sachgruppen und ihre Attribute werden fachlich in einer Excel-Liste
gepflegt (Katalog) und daraus in das JSON-Regelwerk übersetzt.

- **Quelle:** `data/attribute_catalog/20260706_Attribute.xlsx` mit den Spalten
  `Sachgruppe` und `Attribut` (eine Zeile je erlaubtem Attribut).
- **Parser:** `excel.rule_catalog.read_attribute_catalog` liest den Katalog,
  normalisiert die Attributnamen (identisch zum Import) und entfernt Duplikate
  unter Beibehaltung der Reihenfolge.
- **Generator:** `scripts/generate_attribute_rules.py` schreibt daraus
  `config/attribute_rules.json`.

Ablauf zum Aktualisieren der Regeln:

```bash
python scripts/generate_attribute_rules.py
```

### Globale Attribute (`Allgemein`)

Die Sachgruppe `Allgemein` ist **keine** eigenständige Sachgruppe, sondern
definiert **globale Attribute**, die für sämtliche anderen Sachgruppen gelten.

Beim Laden des Regelwerks (`load_attribute_rules`) werden die `Allgemein`-
Attribute automatisch mit den spezifischen Attributen jeder Sachgruppe
zusammengeführt. Dabei gilt:

- **`Allgemein`-Attribute zuerst**, danach die sachgruppenspezifischen,
- **Duplikate entfernt**,
- **Reihenfolge beibehalten** (erstes Auftreten zählt),
- `Allgemein` erscheint danach **nicht** in `known_sachgruppen` und wird von
  `is_known("Allgemein")` als unbekannt gemeldet.

Beispiel: `Allgemein = [Technologie, Typ, Bemerkung]`,
`Diode = [Typ, Wert, Bemerkung]` ⇒
`allowed_for("Diode") = (Technologie, Typ, Bemerkung, Wert)`.

Die Zusammenführung geschieht ausschliesslich beim Laden – der Katalog und die
generierte `attribute_rules.json` enthalten `Allgemein` weiterhin unverändert
als eigenen Abschnitt. Die Excel-Masterdatei bleibt unberührt.

### Regelprüfung und Ergebnis

`rules.rule_engine` prüft je Artikel gegen das Regelwerk (`validate_article` /
`validate_articles`) und liefert `models.ArticleValidationResult` mit:

- `article_number`, `sachgruppenklasse`,
- `allowed_attributes` (für die Sachgruppe erlaubt),
- `missing_attributes` (erlaubt, aber leer/fehlend),
- `disallowed_filled_attributes` (gefüllt, aber nicht vorgesehen),
- `status` (`OK`, `UNKNOWN_SACHGRUPPE`, `ISSUES_FOUND`).

Es werden **keine** Werte verändert – nur geprüft.

### Neue Sachgruppe ergänzen

1. Im Katalog (`data/attribute_catalog/…xlsx`) je erlaubtem Attribut eine Zeile
   mit der neuen `Sachgruppe` und dem `Attribut` ergänzen.
2. Kommt eine neue Attributspalte mit abweichender Schreibweise hinzu,
   zusätzlich eine Zuordnung in `excel.columns.COLUMN_RENAME_MAP` ergänzen.
3. Regelwerk neu generieren: `python scripts/generate_attribute_rules.py`.
4. Kein Code der Regelprüfung muss geändert werden.

`config/attribute_rules.json` ist eine generierte Datei und sollte nicht von
Hand bearbeitet werden.

## Abhängigkeitsrichtung

Um Kopplung gering zu halten, gilt eine klare Abhängigkeitsrichtung:

- `gui` und `app` dürfen von den Fachmodulen abhängen.
- Fachmodule (`analysis`, `rules`, `excel`, `manufacturers`, `ai`) dürfen von
  `models`, `config` und `datasources` abhängen.
- `models` hängt von nichts aus dem Paket ab (Kern des Vokabulars).
- Fachmodule hängen **nicht** von `gui` ab.

## Integration neuer Module

Zum Ergänzen einer neuen Funktion (z. B. einer neuen Datenquelle oder eines
neuen Analyseschritts):

1. **Passendes Paket wählen** oder ein neues, klar benanntes Paket unter
   `src/avor_smart_attribute_manager/` anlegen (mit `__init__.py` und
   aussagekräftigem Modul-Docstring).
2. **Gegen bestehende Schnittstellen programmieren** – z. B. eine neue
   Datenquelle von `datasources.base.DataSource` ableiten, statt Fachmodule
   direkt zu koppeln.
3. **Gemeinsame Datenstrukturen in `models`** ergänzen, falls nötig, damit
   mehrere Module dasselbe Vokabular nutzen.
4. **GUI zuletzt anbinden**: Die Oberfläche ruft das neue Modul auf; die Logik
   bleibt GUI-frei und testbar.
5. **Tests hinzufügen** unter `tests/`, gespiegelt zur Paketstruktur.
6. **Grundprinzipien einhalten**: nur Vorschläge, Originaldaten nie verändern,
   Nachvollziehbarkeit sicherstellen.

## Werkzeuge und Qualität

- **Packaging/Konfiguration:** `pyproject.toml` (setuptools, `src`-Layout).
- **Linting/Formatierung:** `ruff` (inkl. Import-Sortierung und Docstring-
  Prüfung, Google-Konvention).
- **Typprüfung:** `mypy` (strikt).
- **Tests:** `pytest`.

Siehe `README.md` für die konkreten Befehle.

## Offene Annahmen

Diese Punkte wurden bewusst offen gelassen, um keine verfrühten Annahmen zu
treffen (Details siehe Pull-Request-Beschreibung):

- Als Basisspalten werden `ARTIKELNUMMER` und `SACHGRUPPENKLASSE` angenommen;
  bei abweichenden Bezeichnungen sind `excel.columns` und ggf. der Import
  anzupassen.
- Das Regelwerk (`config/attribute_rules.json`) wird aus dem Attribut-Katalog
  generiert (27 Sachgruppen). Es wird angenommen, dass die
  `SACHGRUPPENKLASSE`-Werte der ERP-Exporte den `Sachgruppe`-Namen des Katalogs
  entsprechen.
- Alle erlaubten Attribute gelten aktuell als relevant (fehlend = leer). Eine
  Unterscheidung „Pflicht vs. optional“ ist bewusst noch nicht umgesetzt.
- Externe Datenquellen und KI-Anbindung sind bewusst noch nicht umgesetzt.
