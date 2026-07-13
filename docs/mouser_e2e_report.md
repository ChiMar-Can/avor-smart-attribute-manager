# Mouser-Ende-zu-Ende-Test – Auswertung (PR #5)

Dieser Bericht dokumentiert einen **echten** Ende-zu-Ende-Lauf des
Mouser-Online-Abgleichs gegen die offizielle Mouser Search API mit einer
ERP-Beispieldatei (18 Artikel, je ein Artikel pro Artikelgruppe/Sachgruppe).

Alle Angaben sind **anonymisiert**: keine realen Artikelnummern, Hersteller-
oder Firmendaten, keine Rohantworten mit realen Projektdaten. Die Beispieldatei
und die erzeugte Ausgabedatei sind **nicht** Teil des Repositories.

## 1. Testaufbau

- Aufruf: `python main.py analyse "<ERP-Datei>" --online --no-cache`
- Schlüssel: ausschliesslich aus dem Session-Secret `MOUSER_API_KEY`
  (nie geloggt, nie committet).
- Datensatz: 18 Artikel, 16 verschiedene Sachgruppen.

### Technische Verifikation

| Prüfung | Ergebnis |
| --- | --- |
| API-Verbindung / Key erkannt | OK |
| Alle 18 Artikel verarbeitet | OK |
| Fehler einzelner Artikel isoliert (kein Abbruch) | OK (keine API-Fehler aufgetreten) |
| Ausgabedatei erzeugt (`<Name>_analyse.xlsx`) | OK |
| Blätter `Analyse`, `Zusammenfassung`, `Online_Vorschlaege`, `Online_Abgleich` | vorhanden |
| Originalspalten unverändert & vorangestellt | OK |
| Kein API-Schlüssel in der Excel (roher XML-Scan) | OK |
| Keine vollständigen Rohantworten in der Excel | OK |

## 2. Aggregierte Ergebnisse (anonymisiert)

| Kennzahl | Anzahl |
| --- | ---: |
| Angefragte Artikel | 18 |
| Artikel mit Herstellerteilenummer | 16 |
| `EXACT_MATCH` | 7 |
| `MULTIPLE_EXACT_MATCHES` | 0 |
| `MANUFACTURER_MISMATCH` | 6 |
| `NO_EXACT_MATCH` | 3 |
| `NO_MPN` (keine `HerstellerNr`) | 2 |
| API- oder Rate-Limit-Fehler | 0 |
| Erzeugte Attributvorschläge | 0 |
| Bestätigte ERP-Werte | 0 |
| Erkannte Konflikte | 0 |

## 3. Zentrale Erkenntnis: Mouser Search API liefert keine technischen Kenngrössen

Die wichtigste Feststellung des echten Tests:

> Die Mouser Search API liefert im strukturierten Feld `ProductAttributes`
> **ausschliesslich Verpackungs-/Bestellattribute** – konkret `Verpackung`
> (z. B. „Reel“, „Cut Tape“, „MouseReel“) und `Standardpackungsmenge`.
> **Technische Kenngrössen** (Widerstand, Kapazität, Toleranz, Spannung, Strom,
> Leistung, Dielektrikum, Bauform, …) sind dort **nicht** enthalten.

Das gilt für beide Endpunkte (`search/keyword` und `search/partnumber`). Die
technischen Daten stehen nur im Freitextfeld `Description`, z. B.:

```
"Dickfilmwiderstände - SMD 1/8Watt 1.4Kohms 1%"
"Schottky Dioden & Gleichrichter 30V 200mW"
```

Laut Regelwerk (AGENTS.md, PR-#4-Vorgabe) dürfen Werte **nicht** aus der
Beschreibung/Benennung abgeleitet werden. Daher ist das Ergebnis „0 strukturierte
Attributvorschläge“ **fachlich korrekt** und **kein Fehler des Mappings**: Es
gibt schlicht keine strukturierten Fachparameter, die regelkonform abbildbar
wären.

### Weitere Datenvariante: Lokalisierung

Die Antworten sind auf die im API-Konto hinterlegte Länderseite lokalisiert
(hier `mouser.ch/de`). Attributnamen kommen dadurch **auf Deutsch** zurück
(`Verpackung`, `Standardpackungsmenge`). Ein künftiges technisches Mapping muss
also lokalisierungsfähig sein (mindestens DE/EN). Die Suche selbst kennt keinen
dokumentierten Locale-Parameter; die Sprache folgt dem Konto/der Länderseite.

## 4. Mapping-Prüfung je Attributtyp

Geprüft anhand der realen Antworten für die exakten Treffer. Da nur
Verpackungsattribute geliefert wurden, konnte **kein** technisches Attribut aus
strukturierten Parametern gewonnen werden:

| Attribut | Verwendeter Mouser-Parameter | Eindeutig? | Normalisierung | Regelkonform? |
| --- | --- | --- | --- | --- |
| Technologie | – (nicht geliefert) | – | – | – |
| Typ | – (nicht geliefert) | – | – | – |
| Bauform | – (nicht geliefert) | – | – | – |
| SmdBauform | – (nicht geliefert) | – | – | – |
| Wert | – (nur in `Description`) | – | – | – |
| Toleranz | – (nur in `Description`) | – | – | – |
| Spannung | – (nur in `Description`) | – | – | – |
| Strom | – (nur in `Description`) | – | – | – |
| Leistung | – (nur in `Description`) | – | – | – |
| Dielektrikum | – (nicht geliefert) | – | – | – |

Die einzigen strukturierten Parameter (`Verpackung`, `Standardpackungsmenge`)
sind **nicht** auf ERP-Attribute abbildbar und werden korrekt ignoriert
(keine Falschvorschläge). Dies ist als Regressionstest fixiert
(`tests/test_mouser_response_shape.py`).

## 5. Herstellerabgleich

Sechs Artikel wurden als `MANUFACTURER_MISMATCH` klassifiziert. Zwei
wiederkehrende, fachlich relevante Muster:

1. **Platzhalter-Hersteller im ERP** (z. B. ein generischer Sammelbegriff für
   „diverse“ Hersteller). Der ERP-Wert ist kein echter Herstellername, führt
   aber gegen den konkreten Mouser-Hersteller zwangsläufig zu einer Abweichung.
2. **Abweichende juristische Firmennamen** (z. B. Landesgesellschaft mit
   Rechtsform-Zusatz im ERP vs. Kurzform bei Mouser).

Beide Fälle sind **korrekt** als „Abweichung/Prüfhinweis“ markiert (der exakte
Herstellervergleich ist bewusst konservativ). Verbesserungen (siehe unten)
würden die Trefferquote erhöhen, ändern aber nichts an den Attributvorschlägen,
solange keine technischen Parameter verfügbar sind.

## 6. Cache-Verhalten (verifiziert)

- Zweiter Lauf mit aktiviertem Cache: **0** erneute API-Aufrufe (erster Lauf 17),
  Ergebnisse identisch.
- Cache-Einträge enthalten `provider`, `mpn`, `manufacturer`, `stored_at`
  (Zeitstempel) und das neutrale `result` – **kein** API-Schlüssel.
- `--clear-cache` leert den Cache vollständig.

## 7. Behobene, durch den Test nachgewiesene Fehler

- **API-Schlüssel-Leck in Fehlermeldungen (behoben).** Der Schlüssel wird als
  Query-Parameter an die Anfrage-URL gehängt; `requests` nimmt diese URL in
  Ausnahmemeldungen auf. Diese Meldungen werden in die Excel-Spalte `Meldung`
  (`Online_Abgleich`) geschrieben. Der Schlüssel wird nun aus allen
  Fehlermeldungen redigiert (`MouserProvider._redact`), abgesichert durch
  `tests/test_mouser_provider.py::test_api_key_never_leaks_into_error_message`.

## 8. Bekannte Einschränkungen

- Über die Mouser Search API sind **keine** strukturierten technischen
  Kenngrössen verfügbar; damit sind mit der aktuellen, regelkonformen Logik
  keine technischen Attributvorschläge möglich.
- Antworten sind sprach-/länder-lokalisiert (kontoabhängig).
- Der exakte Herstellervergleich behandelt Platzhalter-Hersteller und
  abweichende Firmen-Schreibweisen (noch) als Abweichung.

## 9. Empfehlungen für den nächsten Schritt

Ohne Verletzung der Grundregeln (keine Beschreibung/Benennung als Quelle, kein
Raten, keine automatische ERP-Änderung):

1. **Parametrische Datenquelle evaluieren.** Für strukturierte technische
   Attribute ist ein Provider mit parametrischen Daten nötig (z. B. Nexar/Octopart
   oder DigiKey). Die providerneutrale Architektur erlaubt dies ohne Änderung der
   Fachlogik.
2. **Lokalisierungsfähiges Mapping** vorbereiten (DE/EN-Parameternamen), damit
   ein künftiger parametrischer Provider unabhängig von der Kontosprache greift.
3. **Herstellerabgleich verbessern** (optional, nach fachlicher Freigabe):
   Platzhalter-Hersteller wie „diverse“ als „nicht gesetzt“ behandeln und
   Rechtsform-Zusätze bei der Namensnormalisierung ignorieren.
4. **Optionaler, ausdrücklich freigegebener Beschreibungs-Parser** als reiner
   *Prüfhinweis* (Konfidenz niedrig) – nur falls fachlich gewünscht; standardmässig
   deaktiviert, da die Beschreibung laut Regelwerk keine verlässliche Quelle ist.
