# Nexar-Provider (Supply GraphQL / `supSearchMpn`)

Dieses Dokument beschreibt die Anbindung von **Nexar** (Octopart) als dritten
providerneutralen Online-Datenanbieter – parallel und unabhängig zu Mouser und
DigiKey. Nexar ersetzt keinen bestehenden Provider; alle drei sind einzeln oder
gemeinsam nutzbar.

> **Status:** Die Integration stützt sich auf die öffentliche Nexar-GraphQL-
> Introspection (verifiziertes Schema, siehe unten) sowie anonymisierte
> Mock-Fixtures in den Tests. Ein **Live-E2E-Lauf wurde durchgeführt** (OAuth2
> Client Credentials, 18-Artikel-Beispieldatei) — Ergebnisse siehe
> „Live-Ende-zu-Ende-Ergebnisse (anonymisiert)“.

## Architektur

- Nexar ist ein eigenständiger Provider (`NexarProvider`) hinter der bestehenden
  Schnittstelle `ComponentDataProvider`.
- GraphQL-spezifische Strukturen (Query, Variablen, `data`/`errors`-Auswertung)
  sind vollständig im Nexar-Adapter (`datasources/nexar.py`) gekapselt.
- Die Antwort wird in das neutrale Datenmodell (`ProviderProduct` inkl.
  strukturierter `ProviderSpec`-Objekte / `ProviderSearchResult`) überführt.
- Die Fachanalyse (`analysis/online_analyzer.py`,
  `analysis/attribute_mapping.py`) arbeitet ausschliesslich mit dem neutralen
  Modell und **kennt GraphQL nicht**.

## Offizielle Endpunkte

| Zweck | Endpunkt |
| --- | --- |
| OAuth2 Token | `POST https://identity.nexar.com/connect/token` |
| GraphQL | `POST https://api.nexar.com/graphql` |

## Authentifizierung

Es werden zwei Wege unterstützt (in dieser Priorität):

1. **Statisches Access-Token** – `NEXAR_ACCESS_TOKEN`, falls gesetzt. Es wird
   direkt als `Authorization: Bearer …` verwendet und kann **nicht** erneuert
   werden; bei HTTP 401 / GraphQL-Auth-Fehler wird kein sinnloser Retry
   ausgeführt, sondern ein `AUTH_ERROR` gemeldet.
2. **OAuth2 Client Credentials** – `NEXAR_CLIENT_ID` + `NEXAR_CLIENT_SECRET`.
   Der Token wird nur im Speicher gehalten, mit Ablaufmarge (30 s)
   wiederverwendet und bei Ablauf bzw. HTTP 401 / GraphQL-Auth-Fehler verworfen
   und neu geholt.
3. Ist **keines** von beidem vorhanden, wird eine verständliche
   `MissingApiKeyError`-Konfigurationsmeldung ausgelöst.

**Sicherheit:** Client-Secret und Token werden niemals geloggt, gecacht oder in
Fehlermeldungen ausgegeben (Redaktion über `_redact`). Der `Authorization`-Header
wird nicht gespeichert. Es werden keine vollständigen Roh-GraphQL-Antworten in
Excel oder ins Repository geschrieben.

## Konfiguration

| Einstellung | Umgebungsvariable | CLI | Standard |
| --- | --- | --- | --- |
| Provider wählen | `AVOR_PROVIDER=nexar` | `--provider nexar` | `mouser` |
| Statisches Token | `NEXAR_ACCESS_TOKEN` | – | – |
| Client-ID | `NEXAR_CLIENT_ID` | – | – |
| Client-Secret | `NEXAR_CLIENT_SECRET` | – | – |
| Token-URL | `NEXAR_TOKEN_URL` | – | `https://identity.nexar.com/connect/token` |
| GraphQL-URL | `NEXAR_GRAPHQL_URL` | – | `https://api.nexar.com/graphql` |

## GraphQL-Query und Schema

Verwendet wird `supSearchMpn` für die Einzel-MPN-Suche. Über die
GraphQL-Introspection wurden die **Pflichtargumente** `rankingMethod`
(`SupSearchRankingMethod!`, Werte `DEFAULT` / `SUPPLY` / `DESIGN`) und
`distributorApiTimeout` (`String!`) bestätigt.

```graphql
query AvorNexarMpnSearch(
  $mpn: String!
  $limit: Int!
  $country: String!
  $currency: String!
  $rankingMethod: SupSearchRankingMethod!
  $distributorApiTimeout: String!
) {
  supSearchMpn(
    q: $mpn
    limit: $limit
    country: $country
    currency: $currency
    rankingMethod: $rankingMethod
    distributorApi: false
    distributorApiTimeout: $distributorApiTimeout
  ) {
    hits
    results {
      part {
        mpn
        manufacturer { name }
        shortDescription
        octopartUrl
        category { name }
        bestDatasheet { url }
        specs {
          attribute { name shortname group }
          displayValue
          value
          units
          unitsSymbol
        }
      }
    }
  }
}
```

Standardwerte: `country=CH`, `currency=CHF`, `rankingMethod=DEFAULT`,
`distributorApiTimeout=20s`, `distributorApi=false` (keine Live-Distributor-
Abfrage, da nur strukturierte technische Daten benötigt werden).

### Verfügbare strukturierte Felder → neutrales Modell

| Nexar (`SupPart`) | Neutrales Modell |
| --- | --- |
| `mpn` | `manufacturer_part_number` |
| `manufacturer.name` | `manufacturer` |
| `shortDescription` | `description` (nur Info, **nie** Attributquelle) |
| `category.name` | `category` |
| `bestDatasheet.url` | `datasheet_url` |
| `octopartUrl` | `product_url` |
| `specs[]` | `specs[]` (`ProviderSpec`: `name`, `display_value`, `raw_value`, `unit`) |

`specs[].attribute.shortname` wird als stabiler Name bevorzugt (Fallback `name`);
`unitsSymbol` als Einheit bevorzugt (Fallback `units`).

## Attribut-Mapping (datengetrieben)

Das Nexar-Mapping ist zentral in
`config/provider_mappings/nexar_attribute_mapping.json` konfiguriert und wird von
`analysis/attribute_mapping.py` (`map_nexar_detailed`) geladen. Jede Regel
definiert:

- `erp_attribute` – internes ERP-Zielattribut,
- `nexar_shortname` + `alternative_names` – Nexar-Spezifikationsname(n),
- `allowed_sachgruppen` – Sachgruppen, für die die Regel gilt (leer = alle),
- `expected_unit` – erwartete Einheit (Prüfung gegen Mehrdeutigkeit),
- `priority` – Priorität bei mehreren passenden Regeln (kleiner = höher).

Regeln:

- Es werden **ausschliesslich strukturierte Spezifikationen** (`specs`)
  verwendet; `shortDescription`/Freitext erzeugt **nie** einen Vorschlag.
- Es dürfen nur Attribute vorgeschlagen werden, die laut
  `config/attribute_rules.json` für die jeweilige Sachgruppe erlaubt sind.
- Bei **mehrdeutigen oder fehlenden Einheiten** (erwartete Einheit gesetzt, aber
  Quell-Einheit fehlt oder weicht ab) wird **kein** Vorschlag erzeugt.
- Rohwert (`value`), Einheit (`unitsSymbol`/`units`) und Quell-Parametername
  bleiben zur Nachvollziehbarkeit erhalten (Spalten `Rohwert`, `Einheit`,
  `Quelle_Parameter`).

Das Mapping kann ohne Codeänderung erweitert werden: neue Regel in der JSON-Datei
ergänzen (der Loader ist gecacht – in einem laufenden Prozess ggf. neu starten).

## Match- und Fehlerstatus

Der Abgleich erfolgt ausschliesslich über `HerstellerNr` (und optional
`Hersteller`); `SachGruppe` dient nur der Plausibilität. Ein Treffer gilt nur bei
**exakter** MPN-Übereinstimmung nach rein technischer Normalisierung (Trim /
unsichtbare Zeichen / Gross-Kleinschreibung – **keine** Suffix-/Packaging-
Entfernung).

| Status | Bedeutung |
| --- | --- |
| `EXACT_MATCH` / `MULTIPLE_EXACT_MATCHES` | genau ein / mehrere exakte Treffer |
| `MANUFACTURER_MISMATCH` | MPN passt, Hersteller weicht ab |
| `NO_EXACT_MATCH` / `NO_MPN` | kein exakter Treffer / keine HerstellerNr |
| `AUTH_ERROR` | Authentifizierung abgelehnt (inkl. abgelaufenes Token) |
| `RATE_LIMITED` | HTTP 429 oder GraphQL-Throttling |
| `PART_LIMIT_REACHED` | Teile-/Kontingentlimit erreicht (GraphQL) |
| `GRAPHQL_ERROR` | sonstiger GraphQL-Fehler (auch bei HTTP 200) |
| `API_ERROR` | HTTP-/Transport-/JSON-Fehler |

**Token-Ablauf:** Ein abgelaufenes/ungültiges Token wird bei OAuth intern
verworfen und neu geholt; nach aussen bleibt der Zustand `AUTH_ERROR` (es gibt
bewusst keinen separaten `TOKEN_EXPIRED`-Status, um das neutrale Modell schlank
zu halten). GraphQL-Fehler werden **auch bei HTTP 200** erkannt und klassifiziert.

## Cache

- Getrennt je Provider und Query-/Schema-Version (Providername
  `nexar-search-mpn-v1`), damit Ergebnisse verschiedener Query-Versionen sich
  nicht vermischen.
- Schlüssel aus normalisierter MPN und optional Hersteller; Zeitstempel und TTL.
- Strukturierte Spezifikationen (`ProviderSpec`) werden mitgespeichert und beim
  Lesen rekonstruiert.
- Es werden **keine** Zugangsdaten, Tokens, Authorization-Header oder
  vollständigen Roh-GraphQL-Antworten gespeichert.
- Fehlerantworten (Auth/GraphQL/Limit/API) werden **nicht** als gültiges Ergebnis
  gecacht.

## Provider-Vergleich

Bei mehreren Providern wird je Artikel ein Quellenvergleich berechnet und optional
als Blatt `Provider_Vergleich` exportiert. Nexar erscheint dort **separat** neben
Mouser und DigiKey. Nur strukturierte technische Werte zählen zur
Quellenübereinstimmung. Statuswerte: `SOURCES_AGREE`,
`MULTIPLE_STRUCTURED_SOURCES_AGREE` (≥3 Quellen), `SOURCES_CONFLICT`,
`ONLY_MOUSER_DATA` / `ONLY_DIGIKEY_DATA` / `ONLY_NEXAR_DATA`, `NO_TECHNICAL_DATA`.

## CLI-Beispiele

```bash
# Nur Nexar
python main.py analyse "ERP_Export.xlsx" --online --provider nexar

# Mehrere Provider parallel und unabhängig
python main.py analyse "ERP_Export.xlsx" --online --provider mouser --provider nexar

# Alle konfigurierten Provider
python main.py analyse "ERP_Export.xlsx" --online --provider all
```

Mehrfachangaben werden dedupliziert und in Eingabereihenfolge verwendet; `all`
löst auf alle unterstützten Provider auf. Ohne `--provider` bleibt das bisherige
Standardverhalten (Provider aus `AVOR_PROVIDER`, Standard `mouser`) erhalten.

## Manueller Ende-zu-Ende-Test (sobald Zugangsdaten vorliegen)

```bash
export NEXAR_ACCESS_TOKEN="…"          # ODER NEXAR_CLIENT_ID/NEXAR_CLIENT_SECRET
python main.py analyse "<ERP-Beispieldatei>" --online --provider nexar --no-cache
# Zweiter Lauf mit Cache zur Verifikation (identische Ergebnisse, keine erneuten Calls)
python main.py analyse "<ERP-Beispieldatei>" --online --provider nexar
```

Zu prüfen: Token-/Verbindungs-Erfolg, Match-Status, tatsächlich gelieferte
strukturierte Spezifikationen je Sachgruppe, resultierende Vorschläge sowie der
Vergleich mit Mouser. Ergebnisse anonymisiert dokumentieren (keine realen
Artikel-/Firmendaten, keine Zugangsdaten, keine Roh-GraphQL-Antworten committen).

## Live-Ende-zu-Ende-Ergebnisse (anonymisiert)

Durchgeführt mit OAuth2 Client Credentials (`NEXAR_CLIENT_ID`/`NEXAR_CLIENT_SECRET`,
nur Session-Secret) gegen die 18-Artikel-ERP-Beispieldatei. Die Datei, die
Ausgabedatei, Roh-GraphQL-Antworten und Zugangsdaten wurden **nicht** committet.

**Verbindung/Auth:** OAuth2-Token wird korrekt geholt; alle 18 Artikel werden
verarbeitet; keine API-/Rate-Limit-Fehler; Einzelfehler brechen den Lauf nicht ab.

**Match-Status (18 Artikel):**

| Status | Anzahl |
| --- | --- |
| Exakter Treffer (`EXACT_MATCH`) | 6 |
| Herstellerabweichung (`MANUFACTURER_MISMATCH`) | 7 |
| Mehrere exakte Treffer (`MULTIPLE_EXACT_MATCHES`) | 1 |
| Kein exakter Treffer (`NO_EXACT_MATCH`) | 3 |
| Keine Herstellerteilenummer (`NO_MPN`) | 1 |
| API-/Rate-Limit-Fehler | 0 |

**Strukturierte Spezifikationen:** Nexar liefert pro Treffer viele strukturierte
`SupSpec`-Parameter (bei Treffern typ. 13–42 Spezifikationen). Das ist der
entscheidende Unterschied zum Mouser-Live-Lauf, bei dem strukturiert im
Wesentlichen nur Verpackungs-/Versanddaten ankamen und die technischen Werte im
nicht nutzbaren Freitext `Description` standen.

**Erzeugte Vorschläge:** 14 gesamt

| Aktion | Anzahl |
| --- | --- |
| Bestätigt (`BESTAETIGT`) | 5 |
| Konflikt prüfen (`KONFLIKT_PRUEFEN`) | 6 |
| Ergänzen (`ERGAENZEN`) | 3 |

Betroffene ERP-Attribute (aus strukturierten Parametern): `Bauform` (4),
`Wert` (3), `Toleranz` (3), `Leistung`, `Dielektrikum`, `Spannung`, `SmdBauform`.
Genutzte Nexar-Quellparameter u. a.: `resistance`, `capacitance`, `inductance`,
`tolerance`, `powerrating`, `voltagerating_dc_`, `dielectric`, `Case/Package`,
`Case Code (Imperial)`. Konfidenz: 4× Hoch, 10× Niedrig (niedrig v. a. bei
Herstellerabweichung bzw. mehreren Treffern — regelkonform als Prüfhinweis).

**Cache verifiziert:** Ein zweiter Lauf mit **absichtlich ungültigen**
Zugangsdaten lieferte identische Ergebnisse (6 exakte Treffer, 14 Vorschläge) —
Beweis, dass ausschließlich der Cache genutzt und keine erneute API-Abfrage
ausgeführt wurde. Die Cache-Dateien (`.cache/nexar-search-mpn-v1/`) enthalten nur
das neutrale Produktmodell, normalisierte MPN und Zeitstempel; ein Scan bestätigte
**keine** Zugangsdaten/Token/`Authorization`-Header und keine vollständige
Roh-GraphQL-Antwort. `--clear-cache` leert den Cache.

**Vergleich mit Mouser:** Identische Beispieldatei — Mouser: 0 technische
Vorschläge (strukturiert nur Verpackung); Nexar: 14 Vorschläge aus echten
strukturierten technischen Parametern. Nexar ist damit die bislang ergiebigste
strukturierte Quelle für unseren Anwendungsfall.

## Batching (Ausblick)

`supMultiMatch` existiert für Batch-Suchen, wird aber **noch nicht** verwendet:
Limits, Rückgabestruktur und Komplexität sind nicht ausreichend geklärt. Die
Architektur (neutrales Modell, providergetrennter Cache, MPN-Dedup) bleibt für
eine spätere Batching-Erweiterung offen.

## Einschränkungen

- Der Live-E2E-Lauf bestätigte reichhaltige strukturierte Spezifikationen; die
  vollständige Abdeckung je Sachgruppe hängt vom jeweiligen Nexar-Katalogdatensatz
  ab und kann bei einzelnen Teilen (0 Spezifikationen) fehlen.
- Es werden nur eindeutig strukturierte Spezifikationen gemappt; mehrdeutige
  Werte/Einheiten werden bewusst **nicht** geraten.
- `shortDescription`/Freitext dient nie als Attributquelle.
