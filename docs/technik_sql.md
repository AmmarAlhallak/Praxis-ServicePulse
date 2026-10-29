# Dateien, Datenfluss und SQL

## Datenbankentscheidung

**DuckDB bleibt die einzige Anwendungsdatenbank.** `data/processed/servicepulse.duckdb` ist eine lokale eingebettete Datei; es gibt keinen separat zu administrierenden Datenbankserver, keine Zugangsdaten und keinen zusätzlichen SQL-Dienst.

SQLite wird ausschließlich durch `sqlite3` aus der Python-Standardbibliothek in `servicepulse/raw.py` benutzt, um die original gelieferten Haier-Rohdaten im Read-only-Modus zu lesen. Diese Datei ist ein wissenschaftliches Quellformat, kein zweiter ServicePulse-Datenspeicher. Die App benötigt diese SQLite-Stichprobe nicht für ihre regulären Parquet-Analysen. Kein SQLite-Paket und kein zusätzlicher SQLite-Server sind erforderlich.

## Zuständigkeiten der vorhandenen Python-Dateien

| Datei | Funktion |
|---|---|
| `app.py` | Streamlit-Oberfläche, Geräte-/Kategorie-/Datumsfilter, Kennzahlen, Plotly-Diagramme, Geräteanalyse, CSV-Export, Import und Quellenhinweise. Einstieg immer über `python -m streamlit run app.py` |
| `servicepulse/presentation.py` | deutsche Kategorien, Messgrößen, Einheiten und Tabellenbezeichnungen; Diagramme und CSV-Lesehilfen auf Kopien ohne Änderung der Originaldaten |
| `servicepulse/imports.py` | lokaler Parquet-Import mit Dateinamen-/Schema-/Größenprüfung und exklusiver Dateierstellung zum Schutz vorhandener Dateien |
| `servicepulse/research.py` | klarer Servicefilterzustand, belegte Falltexte, stündliche Abdeckungsübersicht und Aktualitätsprüfung lokaler Nachweise |
| `servicepulse/faults.py` | passendes Excel-Blatt erkennen, Originalspalten erhalten, ID/Datum/Kategorie normalisieren, Quellzeilen mitführen, filtern, Kennzahlen und Qualität berechnen, Kontrollblatt und Autoren-CSV vergleichen |
| `servicepulse/measurements.py` | Dateischema/ID/Zeilenanzahl prüfen, Messdateien inventarisieren, verfügbare numerische Messgrößen ermitteln, Zeitgrenzen abfragen, SQL-Fensteraggregate, Geräteereignisse, Uhrenoffsets und Vollprüfung pro Datei |
| `servicepulse/storage.py` | kleine Tabellen in DuckDB speichern und zwei SQL-Views definieren |
| `servicepulse/raw.py` | eigene Revco-DAT- und Haier-SQLite-Leser für kontrollierte Rohdatenprüfungen; Kennungskonflikte melden, Haier-RTD zeitbasiert zuordnen |
| `servicepulse/__init__.py` | Kennzeichnung des Python-Pakets, keine eigene Verarbeitung |
| `scripts/build.py` | Excel aufbereiten, Kontroll-/Metadatentabellen, `faults.parquet` und DuckDB erzeugen, alle Parquet-Dateien auf Zeit-/RTD-Qualität prüfen |
| `scripts/check_local.py` | vorhandenen Build schreibgeschützt gegen aktuelle Excel/Dateiliste prüfen; SQL-Views gegen pandas-Ergebnisse vergleichen; bei Abweichung Exitcode 1 |
| `scripts/audit_samples.py` | zwei Rohdatenstichproben prüfen und Messpunktabdeckung aller Servicetage und angrenzenden Siebentagefenster berechnen |
| `scripts/inspect_repository.py` | GitLab-Baum/Commit, Figshare-Metadaten und kleine Referenzdateien über öffentliche APIs abrufen; Netzwerk erforderlich, kein gewöhnlicher App-Startschritt |
| `scripts/download_data.py` | veröffentlichte Parquets einzeln laden, Git-Blob-Hash prüfen, SHA256-Manifest schreiben; für die lokale Demo nicht erneut nötig |
| `scripts/fetch_samples.py` | ausgewählte Serviceberichte und zwei Rohdatenstichproben laden |
| `scripts/fetch_article.py` | Artikelvolltext über Europe PMC laden und Publikationskennung prüfen |
| `tests/test_faults.py` | Excel, Kennzahlen, Kontrollblatt, Filter, ungültige/leere Werte und Quellenkonflikte |
| `tests/test_measurements.py` | Parquet-Schema, SQL-Fenster, Uhrkorrektur, Qualitätsprüfung und DuckDB-Speicherung mit kleinen Testfixtures |
| `tests/test_raw.py` | Rohdatenheader, Kennungskonflikt, Uhrkorrektur und zeitbasierter SQLite-Join mit temporären Testdaten |
| `tests/test_app.py` | App-Start, Excel-Betrieb ohne Messdateien, leere Filter und reale Gerätewechsel |
| `tests/test_local_integration.py` | vorhandene DuckDB gegen echte Quellen, reale SQL-Aggregate gegen unabhängig berechnete pandas-Werte, kombinierte Filter/Diagramme/Reset und VS-Code-Konfiguration |

## Datenfluss und Speicherung

1. Excel ist die maßgebliche Servicequelle. `read_faults` erkennt das echte Datenblatt anhand seiner Spalten. Originalwerte bleiben erhalten; abgeleitete Felder wie `device_id`, `event_date`, `category_group` und `source_row` ergänzen die Daten.
2. Die App liest die kleine Excel direkt mit pandas, sodass ein neu gespeicherter Excel-Stand nicht von einer veralteten Datenbank verdeckt wird. Servicefilter und kleine deskriptive Auswertungen laufen ebenfalls mit pandas.
3. Beim Build werden die normalisierten Serviceeinträge, Dateimetadaten und Qualitätskontrollen in DuckDB gespeichert. Der separate Kontrolllauf erkennt Unterschiede zwischen aktuellem Datenstand und letztem Build.
4. Große Messdateien bleiben unter `data/raw/Revco/` und `data/raw/Haier/`. DuckDB fragt nur die benötigte Datei, Messgröße und Zeitspanne ab und liefert Aggregate an Plotly. Keine Kopie der 181 Millionen Zeilen in eine weitere Datenbank.
5. Servicekalendertage werden nach Geräte-ID auf Messkurven markiert. Bereits korrigierte Temperaturzeitstempel werden nicht erneut verschoben. Separate Geräteereignisse werden mit dem dokumentierten Offset aus `research/reference/data/raw_data/other_data/time_offsets.csv` abgefragt und korrigiert.
6. Vorher/Nachher schließt den Servicetag aus; messpunktgewichtete Mittelwerte, Median und Stichprobenzahlen beschreiben Beobachtungen, keine Reparaturwirkung. `State` bleibt als Bitcode im Original; sein numerischer Mittelwert wird nicht als Messgröße angeboten.

| Speicherort | Inhalt |
|---|---|
| `fault_summary_R1.xlsx` | unveränderte originale Servicequelle |
| `data/raw/{Revco,Haier}/*.parquet` | 106 veröffentlichte Mess-/Geräteereignisdateien |
| `data/processed/servicepulse.duckdb` | `faults`, `measurement_files`, `quality_checks`, Views `category_counts` und `repeated_categories` |
| `data/processed/faults.parquet` | normalisierte Serviceeinträge samt Originalspalten und Zeilenherkunft |
| `data/processed/*.csv`, `summary.json`, `errors.json` | reproduzierbare Kontroll-, Qualitäts- und Abdeckungsberichte sowie Zusammenfassung |
| `research/reference/` | separat aufbewahrter Autorencode und Metadatenquellen |
| `research/samples/` | geprüfte Rohdaten- und Serviceberichtstichproben |
| `.venv/` | lokale Python-Umgebung; kein Projektdatenbestand |

## Tatsächlich verwendete SQL-Abfragen

In `storage.py` registriert DuckDB zunächst einen kleinen pandas-DataFrame als temporäre Relation `incoming` und speichert ihn mit folgendem Muster. Der Tabellenname ist ein fest im Code definierter Wert:

```sql
CREATE OR REPLACE TABLE faults AS SELECT * FROM incoming;
```

Entsprechend werden `measurement_files` und `quality_checks` erzeugt. Die Views lauten:

```sql
CREATE OR REPLACE VIEW category_counts AS
SELECT category, count(*) AS entries,
       count(DISTINCT device_id) AS devices
FROM faults
GROUP BY category;

CREATE OR REPLACE VIEW repeated_categories AS
SELECT device_id, category, count(*) AS entries
FROM faults
WHERE device_valid
GROUP BY device_id, category
HAVING count(*) > 1;
```

Diese Views gehören zum gespeicherten Build. Die App berechnet gefilterte Servicehäufigkeiten direkt aus der aktuellen Excel; sie liest diese Views nicht für jeden Filter. `check_local.py` prüft ihre Übereinstimmung mit den Quelldaten.

`measurements.py` fragt beispielsweise stündliche RTD-Aggregate direkt gegen Parquet ab:

```sql
SELECT date_trunc('hour', "Datetime") AS time,
       avg("RTD") AS mean, min("RTD") AS minimum,
       max("RTD") AS maximum, count("RTD") AS n
FROM read_parquet(?)
WHERE "Datetime" >= ? AND "Datetime" < ?
GROUP BY 1 ORDER BY 1;
```

Die drei Platzhalter erhalten Dateipfad, Startzeit und exklusive Endzeit als gebundene Parameter. Die Messspalte wird nur nach Abgleich mit dem tatsächlichen Dateischema eingesetzt und als SQL-Bezeichner gequotet; das Intervall kommt aus einer festen erlaubten Liste. Datumseingaben werden nicht als SQL-Text zusammengebaut.

Der Vorher/Nachher-Vergleich führt je Fenster dieses Muster aus:

```sql
SELECT count(*) AS rows, count("RTD") AS valid,
       avg("RTD") AS mean, median("RTD") AS median,
       min("Datetime") AS first_time, max("Datetime") AS last_time
FROM read_parquet(?)
WHERE "Datetime" >= ? AND "Datetime" < ?;
```

Geräteereignisse werden begrenzt geladen:

```sql
SELECT * FROM read_parquet(?)
WHERE "Datetime" >= ? AND "Datetime" < ?
ORDER BY "Datetime" LIMIT ?;
```

Dabei zieht Python den Uhrenoffset von den Fenstergrenzen ab und addiert ihn anschließend auf die Ergebniszeiten. Die Anzeige ist auf 1.000 Zeilen begrenzt. `time_bounds` verwendet `SELECT min("Datetime"), max("Datetime") FROM read_parquet(?)`; die freie Messansicht beginnt dadurch innerhalb des verfügbaren Gerätezeitraums.

Die Qualitätsprüfung zählt fehlende und wiederholte Zeitstempel und ermittelt RTD-Grenzen. Eine weitere Abfrage verwendet `lag("Datetime") OVER (ORDER BY "Datetime")`, um Messlücken zu bestimmen. Die konkreten ausführbaren Fassungen stehen vollständig in `audit_file`.

Die einzige SQLite-Nutzung liest `SELECT * FROM EACH_POINT_DATA_CHANGE` und `SELECT TIME, TEMPERATURE FROM TEMPER_RECORD` aus der Originaldatei. Die anschließende RTD-Zuordnung erfolgt mit einem expliziten Zeitjoin in pandas; es werden keine ServicePulse-Tabellen in SQLite geschrieben.

Ergänzung der geführten Fallanalyse: `window_comparison` behält die bestehenden Mittelwerte, Mediane und Stichprobenzahlen bei und liefert zusätzlich `min`, `max` und `count(DISTINCT date_trunc('hour', "Datetime")) FILTER (WHERE Messspalte IS NOT NULL)`. `serviceday_summary` fragt dieselben grundlegenden Größen separat für den Kalendertag ab. Die Differenz zwischen den 24 × Tagen des Fensters und der Zahl beobachteter Stunden zählt leere Stundenintervalle; sie ist kein prozentualer Nachweis lückenloser Aufzeichnung. Die Rohdaten und bisherigen SQL-Views bleiben unverändert.
