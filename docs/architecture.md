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

## Datenfluss (vorgesehen)

Der geplante Ablauf verdeutlicht das Zusammenspiel der Module. Er ist noch
**nicht** implementiert und dient als Orientierung:

```
ERP-Excel-Export (nur lesen)
        │
        ▼
   excel.importer  ──►  models  ◄──────────────┐
        │                                       │
        ▼                                       │
   analysis  +  rules   (nutzen models)         │
        │                                       │
        │   (optional, später)                  │
        ▼                                       │
   manufacturers ──► datasources                │
        │                                       │
        ▼                                       │
   ai (optional, nur Vorschläge)                │
        │                                       │
        ▼                                       │
   Vorschläge/Befunde (models) ────────────────┘
        │
        ├──►  gui   (Anzeige, Auswahl)
        └──►  excel.exporter  ──►  NEUE Excel-Datei
```

Die GUI ruft die Fachmodule auf und stellt deren Ergebnisse dar. Die
Fachmodule kennen die GUI nicht und sind dadurch unabhängig testbar.

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

- Konkrete Struktur der ERP-Exporte (Spalten, Attribute) ist noch unbekannt;
  daher enthalten `models` noch keine konkreten Felder.
- Konkrete Qualitätskriterien und Regeln sind noch nicht definiert.
- Externe Datenquellen und KI-Anbindung sind bewusst noch nicht umgesetzt.
