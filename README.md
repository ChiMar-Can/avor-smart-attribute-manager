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

Analyse einer ERP-Excel-Datei (Kommandozeile):

```bash
python main.py analyse "ERP_Export.xlsx"
# oder ohne Argument mit Dateiauswahl-Dialog:
python main.py
# gleichwertig als Modulaufruf:
python -m avor_smart_attribute_manager analyse "ERP_Export.xlsx"
```

Die Eingabedatei wird **ausschliesslich gelesen**. Das Ergebnis wird als neue
Datei `<Dateiname>_analyse.xlsx` daneben geschrieben (siehe unten). Eine GUI
gibt es noch nicht.

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
  (z. B. `Dimmension` → `Dimension`, `SMD-Bauform` → `SmdBauform`). Die
  Artikelnummer-Spalte darf auch `ARTIKEL` heissen (wird auf `ARTIKELNUMMER`
  vereinheitlicht).
- **Nur bekannte Attribute werden geprüft:** Spalten, die im Katalog nicht als
  Attribut vorkommen (ERP-Metadaten wie `Benennung`, `IstBestand`, `Hersteller`,
  `ARTIKELGRUPPE`), bleiben in der Ausgabe erhalten, werden aber **nicht**
  geprüft (keine Falschmeldungen als „unerlaubt gefüllt“).
- **Regelwerk:** je Sachgruppe erlaubte Attribute; **generiert** nach
  `src/avor_smart_attribute_manager/config/attribute_rules.json` (nicht im Code
  und nicht von Hand gepflegt).
- **Ergebnis:** je Artikel Status (`OK`, `UNKNOWN_SACHGRUPPE`, `ISSUES_FOUND`)
  sowie fehlende bzw. unzulässig gefüllte Attribute.

### Analysedatei (`<Dateiname>_analyse.xlsx`)

Der CLI-Befehl `analyse` schreibt eine **neue** Excel-Datei; die Originaldatei
bleibt unverändert. Tabellenblatt `Analyse` enthält **alle Originalspalten**
plus folgende angefügte Spalten (Listen kommagetrennt):

| Spalte | Inhalt |
| --- | --- |
| `Pruefstatus` | `OK` / `Unbekannte Sachgruppe` / `Fehler gefunden` |
| `Erlaubte_Attribute` | laut Regelwerk erlaubte Attribute |
| `Gefuellte_Attribute` | tatsächlich befüllte Attribute |
| `Fehlende_Attribute` | erlaubte, aber leere/fehlende Attribute |
| `Nicht_erlaubte_gefuellte_Attribute` | befüllt, obwohl nicht vorgesehen |
| `Anzahl_fehlender_Attribute` | Anzahl fehlender Attribute |
| `Anzahl_unzulaessiger_Attribute` | Anzahl unzulässig gefüllter Attribute |

Zusätzlich fasst das Tabellenblatt `Zusammenfassung` die Kennzahlen zusammen
(Anzahl Artikel, OK, unbekannte Sachgruppen, Artikel mit fehlenden bzw.
unzulässigen Attributen).

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

## Online-Abgleich über die Herstellerteilenummer (Mouser / DigiKey / Nexar)

Optional können fehlende oder möglicherweise falsche Attribute anhand der
`HerstellerNr` **online** abgeglichen werden. Es werden ausschliesslich
**Vorschläge** erzeugt; ERP-Werte werden **niemals** verändert und **nicht**
automatisch übernommen. Die manuell gepflegte `Benennung` wird **nicht** als
Attributquelle verwendet.

Angebunden sind drei providerneutrale Datenquellen (kein Web-Scraping):

- **Mouser Search API**
- **DigiKey Product Information API** – wahlweise **V3** oder **V4** (konfigurierbar)
- **Nexar Supply GraphQL** (`supSearchMpn`, siehe
  [`docs/nexar_provider.md`](docs/nexar_provider.md))

Die Fachlogik hängt nur von einem gemeinsamen, neutralen Datenmodell ab; alle
drei Provider sind einzeln oder gemeinsam nutzbar, ohne die Analyse zu ändern.
Weitere Quellen (Hersteller-APIs, interne DB, …) lassen sich analog ergänzen.

### Datenquelle wählen

Standard ist Mouser. Die Auswahl erfolgt über die Umgebungsvariable
`AVOR_PROVIDER` (`mouser`/`digikey`/`nexar`) oder pro Lauf über `--provider`.
`--provider` ist **mehrfach** angebbar (unabhängiger, paralleler Abgleich);
`--provider all` nutzt alle konfigurierten Provider:

```bash
python main.py analyse "ERP_Export.xlsx" --online --provider digikey
python main.py analyse "ERP_Export.xlsx" --online --provider digikey --digikey-version v3
python main.py analyse "ERP_Export.xlsx" --online --provider nexar
python main.py analyse "ERP_Export.xlsx" --online --provider mouser --provider nexar
python main.py analyse "ERP_Export.xlsx" --online --provider all
```

Bei mehreren Providern entsteht zusätzlich das Blatt `Provider_Vergleich` mit
einem Quellenvergleich je Artikel.

> **Hinweis (aus dem echten Mouser-Ende-zu-Ende-Test, siehe
> [`docs/mouser_e2e_report.md`](docs/mouser_e2e_report.md)):** Die Mouser Search
> API liefert strukturiert nur **Verpackungsattribute** (`Verpackung`,
> `Standardpackungsmenge`); technische Kenngrössen stehen dort nur im
> Freitextfeld `Description`, das laut Regelwerk **nicht** als Attributquelle
> dienen darf. Die **DigiKey Product Information API** liefert demgegenüber
> strukturierte **technische** Parameter (`Parameters`) und ist damit die
> geeignetere Quelle für Attributvorschläge (siehe
> [`docs/digikey_provider.md`](docs/digikey_provider.md)).

### Mouser-API-Zugang einrichten

1. Bei Mouser registrieren und unter *Mouser API* einen Zugang für die
   **Search API** anfordern: <https://www.mouser.com/api-hub/>.
2. Den erhaltenen API-Schlüssel bereitstellen – **niemals** ins Repository
   committen. Zwei Möglichkeiten:

   ```bash
   # Variante A: Umgebungsvariable
   export MOUSER_API_KEY="dein_schluessel"

   # Variante B: lokale .env-Datei (per .gitignore ausgeschlossen)
   cp .env.example .env    # anschliessend MOUSER_API_KEY eintragen
   ```

### DigiKey-API-Zugang einrichten

1. Bei DigiKey registrieren und unter <https://developer.digikey.com/> eine App
   für die **Product Information API** anlegen (OAuth2, Client Credentials).
2. `Client-ID` und `Client-Secret` bereitstellen – **niemals** ins Repository
   committen:

   ```bash
   export DIGIKEY_CLIENT_ID="deine_client_id"
   export DIGIKEY_CLIENT_SECRET="dein_client_secret"
   export DIGIKEY_API_VERSION="v4"   # oder "v3"
   # alternativ die Werte in eine lokale .env eintragen (siehe .env.example)
   ```

3. Die verwendete API-Version ist über `DIGIKEY_API_VERSION` (bzw.
   `--digikey-version`) frei wählbar und **nicht** in der Fachlogik verdrahtet.
   Für die Sandbox `DIGIKEY_BASE_URL=https://sandbox-api.digikey.com` setzen.

### Nexar-API-Zugang einrichten

1. Bei Nexar registrieren (<https://nexar.com/>) und eine App mit Zugang zur
   **Supply**-API anlegen (OAuth2, Client Credentials).
2. Entweder ein statisches Access-Token **oder** Client-ID/Secret bereitstellen –
   **niemals** ins Repository committen:

   ```bash
   # Variante A: statisches Access-Token (hat Vorrang)
   export NEXAR_ACCESS_TOKEN="dein_token"

   # Variante B: OAuth2 Client Credentials
   export NEXAR_CLIENT_ID="deine_client_id"
   export NEXAR_CLIENT_SECRET="dein_client_secret"
   # alternativ die Werte in eine lokale .env eintragen (siehe .env.example)
   ```

3. Details, GraphQL-Query, Mapping und Einschränkungen:
   [`docs/nexar_provider.md`](docs/nexar_provider.md).

Fehlen die Zugangsdaten des gewählten Providers, bricht der Online-Modus mit
einer verständlichen Meldung ab (die reine Datenqualitätsanalyse funktioniert
weiterhin ohne Zugangsdaten).

### Online-Abgleich starten

```bash
python main.py analyse "ERP_Export.xlsx" --online
# Provider/Version wählen:
python main.py analyse "ERP_Export.xlsx" --online --provider digikey --digikey-version v4
# Cache umgehen bzw. vorher leeren:
python main.py analyse "ERP_Export.xlsx" --online --no-cache
python main.py analyse "ERP_Export.xlsx" --online --clear-cache
```

Die Ausgabe erweitert die Analysedatei um zwei Tabellenblätter (die Blätter
`Analyse` und `Zusammenfassung` bleiben erhalten):

- **`Online_Vorschlaege`** – ein Eintrag je vorgeschlagenem Attribut mit
  Spalten `ARTIKEL`, `SachGruppe`, `Hersteller`, `HerstellerNr`, `Provider`,
  `Match_Status`, `Match_Konfidenz`, `Attribut`, `ERP_Wert`, `Vorschlag`,
  `Aktion`, `Quelle_Produkt`, `Quelle_Datenblatt`, `Begruendung`.
- **`Online_Abgleich`** – eine Zeile je Artikel mit dem allgemeinen Suchstatus.

### Match-Status

| Status | Bedeutung |
| --- | --- |
| `Exakter Treffer` | Teilenummer (technisch normalisiert) und – falls im ERP vorhanden – Hersteller stimmen; genau ein Treffer. |
| `Mehrere exakte Treffer` | Mehrere passende Datensätze; Werte nur bei Konsens vorgeschlagen. |
| `Herstellerabweichung` | Teilenummer passt, Hersteller weicht ab. |
| `Kein exakter Treffer` | Kein Datensatz mit passender Teilenummer. |
| `Keine Herstellerteilenummer` | Im ERP keine `HerstellerNr` hinterlegt. |
| `API-Fehler` / `Rate-Limit` | Technischer Fehler; übrige Artikel werden trotzdem verarbeitet. |
| `Authentifizierungsfehler` / `GraphQL-Fehler` / `Teilelimit erreicht` | Nexar-spezifische Fehlerbilder (Auth/GraphQL/Kontingent). |

### Konfidenz

| Stufe | Kriterien |
| --- | --- |
| `Hoch` | exakte Teilenummer, Hersteller stimmt, genau ein Treffer, strukturiertes Attribut. |
| `Mittel` | exakte Teilenummer, ERP-Hersteller fehlt, genau ein plausibler Treffer. |
| `Niedrig` | mehrere Treffer oder Herstellerabweichung – nur als Prüfhinweis. |

Der `Provider` (z. B. `mouser`, `digikey-v4`, `nexar-search-mpn-v1`) wird je
Vorschlag und je Artikel in der Ausgabe geführt, sodass die verwendete Quelle
nachvollziehbar bleibt. Zusätzlich führen die Vorschläge `Rohwert`, `Einheit` und
`Quelle_Parameter` zur vollständigen Nachvollziehbarkeit.

### Aktion

| Aktion | Bedeutung |
| --- | --- |
| `Ergänzen` | ERP-Wert leer, Online-Wert vorhanden. |
| `Bestätigt` | ERP- und Online-Wert stimmen (nach Einheiten-Normalisierung) überein. |
| `Konflikt prüfen` | ERP- und Online-Wert weichen ab – manuell prüfen. |

### Datenschutz, lokale Verarbeitung und Cache

- Verarbeitung erfolgt lokal; an die jeweilige Provider-API wird **nur** die
  bereinigte Herstellerteilenummer als Suchbegriff gesendet. Zugangsdaten
  (API-Schlüssel bzw. OAuth-Client-Secret/Token) werden **niemals** protokolliert
  oder in Ausgaben/Fehlermeldungen geschrieben (Redaktion).
- Ein lokaler Cache unter `.cache/` (per `.gitignore` ausgeschlossen) vermeidet
  wiederholte Anfragen. Er speichert nur neutrale Produktdaten mit Zeitstempel,
  **keine** API-Schlüssel und **keine** Fehlerantworten. Gültigkeitsdauer und
  Verzeichnis sind konfigurierbar (siehe `.env.example`); `--clear-cache` bzw.
  `--no-cache` steuern ihn zur Laufzeit.
- Fehler werden robust behandelt (Timeout, begrenzte Wiederholungen mit Backoff,
  Rate-Limit-Erkennung); ein Fehler bei einem Artikel stoppt die übrigen nicht.

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
6. **Herstellerdaten & Datenquellen** *(begonnen)* – Abgleich über die
   Herstellerteilenummer; Mouser, DigiKey und Nexar als unabhängige Provider
   über eine gemeinsame, providerneutrale Schnittstelle (weitere Quellen folgen).
7. **KI-Unterstützung** *(optional)* – klar gekapselte, optionale Vorschläge.

## Grundprinzipien

Verbindliche Prinzipien für die Weiterentwicklung sind in
[`AGENTS.md`](AGENTS.md) festgehalten.
