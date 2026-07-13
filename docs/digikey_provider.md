# DigiKey-Provider (Product Information V3/V4)

Dieses Dokument beschreibt die Anbindung von DigiKey als zweiten
providerneutralen Online-Datenanbieter, die Unterschiede zwischen den
API-Versionen **V3** und **V4** sowie eine Bewertung, welche Version sich für
unseren Anwendungsfall (strukturierte technische Attributvorschläge) besser
eignet.

> **Status der Bewertung:** Die Einschätzung stützt sich auf die öffentlich
> dokumentierten Schemata beider API-Versionen, die in den Tests hinterlegten
> anonymisierten Antwort-Fixtures **sowie einen realen Verbindungs-/Auth-Test**
> (siehe Abschnitt „Ergebnis des Live-Tests“). Die inhaltliche
> Parameterabdeckung je Sachgruppe konnte **noch nicht** live bestätigt werden,
> weil der verwendete DigiKey-Account **nicht für die Product Information API
> freigeschaltet** war (HTTP 401, „not subscribed“). Nach Freischaltung kann der
> manuelle E2E-Lauf (siehe unten) die Bewertung präzisieren.

## Ergebnis des Live-Tests (anonymisiert)

Ein realer Lauf über eine ERP-Beispieldatei (18 Artikel) mit temporären
Zugangsdaten hat gezeigt:

- **OAuth2 (Client Credentials) funktioniert:** Der Token-Endpunkt
  (`POST /v1/oauth2/token`, Produktion) lieferte HTTP 200 inkl. `access_token`
  und `expires_in`.
- **Die Produktsuche wurde jedoch mit HTTP 401 abgelehnt** – sowohl V4
  (`detail: "You are not subscribed to this API."`) als auch V3. Ursache ist eine
  **fehlende API-Subscription** des DigiKey-Accounts (nicht ein Code-Fehler).
- **Der Provider verhielt sich korrekt und robust:** Token wurde geholt, der
  401-Status sauber als `API-Fehler` je Artikel dokumentiert, die übrigen Artikel
  weiter verarbeitet; Zugangsdaten wurden **nicht** ausgegeben. Die
  DigiKey-Detailmeldung wird (redigiert) in die Spalte `Meldung` übernommen,
  sodass die Ursache direkt erkennbar ist.
- **Konsequenz:** Verbindung, Authentifizierung und die gesamte Integration
  (CLI-Auswahl, Fehlerbehandlung, Redaktion) sind live bestätigt. Die
  tatsächlich gelieferten strukturierten Parameter je Sachgruppe stehen weiterhin
  unter dem Vorbehalt eines Laufs mit **freigeschaltetem** API-Zugang.

**Zur Freischaltung:** Im DigiKey-Entwicklerportal
(<https://developer.digikey.com/> → *My Apps*) die App der **Product
Information API** (Production, gewünschte Version) zuweisen/abonnieren. Danach den
Live-Lauf (siehe unten) wiederholen.

## Architektur

- DigiKey ist ein eigenständiger Provider (`DigiKeyProvider`) hinter der
  bestehenden Schnittstelle `ComponentDataProvider`.
- Beide API-Versionen liefern in dasselbe neutrale Datenmodell
  (`ProviderProduct` / `ProviderSearchResult`). Die versionsspezifische
  Antwortstruktur ist vollständig im Provider gekapselt.
- Die Fachanalyse (`analysis/online_analyzer.py`, `analysis/attribute_mapping.py`)
  arbeitet ausschliesslich mit dem neutralen Modell und **kennt die API-Version
  nicht**. Sie ist damit provider- und versionsunabhängig.
- Die Versionsauswahl ist konfigurierbar (Umgebungsvariable
  `DIGIKEY_API_VERSION` bzw. CLI-Option `--digikey-version`) und **nicht** in der
  Businesslogik verdrahtet.

## Konfiguration und Versionswechsel

| Einstellung | Umgebungsvariable | CLI | Standard |
| --- | --- | --- | --- |
| Provider wählen | `AVOR_PROVIDER=digikey` | `--provider digikey` | `mouser` |
| API-Version | `DIGIKEY_API_VERSION=v3\|v4` | `--digikey-version v3\|v4` | `v4` |
| Client-ID | `DIGIKEY_CLIENT_ID` | – | – |
| Client-Secret | `DIGIKEY_CLIENT_SECRET` | – | – |
| Basis-URL | `DIGIKEY_BASE_URL` | – | `https://api.digikey.com` |

Der Wechsel zwischen V3 und V4 erfordert **keine** Codeänderung – nur die
Konfiguration.

## Authentifizierung

Beide Versionen nutzen OAuth2 **Client Credentials**:

- Token-Endpunkt: `POST {base_url}/v1/oauth2/token`
  (`grant_type=client_credentials`, `client_id`, `client_secret`).
- Der Access-Token wird **nur im Speicher** gehalten, mit Ablaufmarge
  wiederverwendet und bei HTTP 401 verworfen und neu geholt.
- Client-Secret und Token werden **niemals** geloggt, gecacht oder in
  Fehlermeldungen ausgegeben (Redaktion, siehe `_redact`).

## Unterschiede V3 vs. V4

| Aspekt | V3 | V4 |
| --- | --- | --- |
| Such-Endpunkt | `/Search/v3/Products/Keyword` | `/products/v4/search/keyword` |
| Request-Feld Limit | `RecordCount` | `Limit` |
| MPN-Feld | `ManufacturerPartNumber` | `ManufacturerProductNumber` |
| Hersteller | `Manufacturer.Value` | `Manufacturer.Name` |
| Beschreibung | `ProductDescription` (Freitext) | `Description.ProductDescription` (Freitext) |
| Kategorie | `Category.Value` | `Category.Name` |
| Datenblatt | `PrimaryDatasheet` | `DatasheetUrl` |
| Parameter-Liste | `Parameters[].Parameter` / `.Value` | `Parameters[].ParameterText` / `.ValueText` |

Beide Versionen liefern **strukturierte technische Parameter** (`Parameters`),
z. B. `Resistance`, `Capacitance`, `Tolerance`, `Power (Watts)`,
`Voltage - Rated`, `Supplier Device Package`, `Mounting Type`. Diese werden
sachgruppenabhängig auf die erlaubten ERP-Attribute abgebildet (siehe
`analysis/attribute_mapping.py`). Freitextfelder (`Description`) werden – wie bei
Mouser – **nicht** als Attributquelle verwendet.

## Attribut-Mapping und -Abdeckung

Gemappt werden ausschliesslich eindeutig strukturierte Parameter auf die
erlaubten ERP-Attribute (`Wert`, `Toleranz`, `Leistung`, `Spannung`, `Strom`,
`Bauform`, `SmdBauform`, `Technologie`, `Dielektrikum`, `Typ`). Der `Wert` ist
sachgruppenabhängig (z. B. `Resistance`→Widerstand, `Capacitance`→Kondensator,
`Inductance`→Ferrit/Induktion, `Frequency`→Quarz/Oszillator).

Da V3 und V4 sich inhaltlich fast ausschliesslich in **Feldnamen** (nicht im
Parameter-Vokabular) unterscheiden, ist die **Attributabdeckung beider Versionen
praktisch identisch**. Der Unterschied liegt im Antwort-Schema, das der Provider
kapselt.

## Bewertung: V3 oder V4?

- **Strukturierte technische Daten:** Beide Versionen liefern dieselben
  parametrischen Produktdaten; für die Attributabdeckung ergibt sich **kein
  relevanter Unterschied**.
- **Zukunftssicherheit:** V4 ist die aktuelle, aktiv weiterentwickelte
  Product-Information-API; V3 gilt langfristig als auslaufend. Neue Integrationen
  sollten daher **V4** verwenden (Projekt-Standard: `v4`).
- **Migration:** Da die Fachlogik versionsunabhängig ist und der Wechsel rein
  konfigurativ erfolgt, ist eine Migration auf V4 **risikoarm und empfehlenswert**.
  V3 bleibt für Bestände mit ausschliesslichem V3-Zugang weiterhin nutzbar.

**Empfehlung:** Standardmässig **V4** verwenden; V3 nur, falls für den
konkreten DigiKey-Account nur V3-Zugang besteht.

## Manueller Ende-zu-Ende-Test (sobald Zugangsdaten vorliegen)

```bash
export DIGIKEY_CLIENT_ID="…"
export DIGIKEY_CLIENT_SECRET="…"
export DIGIKEY_API_VERSION="v4"   # oder v3
python main.py analyse "<ERP-Beispieldatei>" --online --provider digikey --no-cache
```

Zu prüfen: Verbindungs-/Token-Erfolg, korrekte Match-Status, tatsächlich
gelieferte strukturierte Parameter je Sachgruppe, resultierende Vorschläge sowie
etwaige V3/V4-Feldabweichungen. Ergebnisse anonymisiert dokumentieren (keine
realen Artikel-/Firmendaten, keine Zugangsdaten).

## Einschränkungen

- Ohne Zugangsdaten ist nur der (mockbasierte) Automatiktest möglich; die
  reale Parameterabdeckung je Sachgruppe steht unter dem Vorbehalt des
  manuellen E2E-Tests.
- Es werden nur eindeutig strukturierte Parameter gemappt; mehrdeutige Parameter
  werden bewusst **nicht** geraten.
- Cache-Einträge werden je Version getrennt gehalten (Providername
  `digikey-v3` / `digikey-v4`), damit V3- und V4-Ergebnisse nicht vermischt
  werden.
