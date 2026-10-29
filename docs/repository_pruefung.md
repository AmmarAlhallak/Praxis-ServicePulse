# Prüfung des Forschungsrepositorys

Prüfdatum 29.10.2026, Projekt-ID 1804, Branch main, Commit `2779f6043fd9d3a7e1b8b1fe0c0f857735684b69`.
Quelle: https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data . Alle Seiten des rekursiven GitLab-Dateibaums wurden abgefragt: 9.133 Einträge, davon 8.862 Dateien. Der normale Git-Clone wurde wegen des großen Gesamtbestands abgebrochen; selektive API-Downloads waren erfolgreich.

## Struktur und tatsächlicher Bestand

| Pfad | geprüfter Inhalt |
|---|---|
| `README.md` | ETL-Architektur und Datenbeschreibung; manche Spaltenbeispiele weichen vom tatsächlichen Dateischema ab |
| `data/dataset/Revco` | 38 Temperatur- und 38 Geräteereignis-Parquets; Kategorienliste und Liste fehlender Monatsdateien |
| `data/dataset/Haier` | 15 Temperatur- und 15 Geräteereignis-Parquets; Ereignisklassen |
| `data/dataset/fault_summary_R1.xlsx` | Servicezusammenfassung und Kategorie-Kontrolltabelle |
| `data/raw_data/Revco` | 8.570 Dateien, vorwiegend monatliche tabulatorgetrennte `.dat`-Temperatur-/Ereignislogs; zusätzliche Unterordner, die der Autorencode ausschließt |
| `data/raw_data/Haier` | 30 Dateien: Konfigurationen und SQLite-Datenbanken |
| `data/raw_data/other_data` | `freezer_faults.csv`, `time_offsets.csv`, `freezers_model_data.csv` |
| `data/raw_data.zip` | zusätzliches Rohdatenarchiv, nicht benötigt und nicht heruntergeladen |
| `data/documentation` | 123 Dateien in Serviceberichtspfaden, außerdem Datenblätter, Handbücher und Kältemittelunterlagen; Dateizahl ist nicht gleich Zahl unabhängiger Servicefälle |
| `data_pipeline.py`, `src/ETL`, `src/resources` | Orchestrierung, Extract/Transform/Load, Konstanten, Plot- und Zustandsdecoder |
| `setup.py` | alte Versionsbindungen u.a. fastparquet 2023.4.0, pyfluids 2.3.2 und pysqlite3 0.5.0; nicht ungeprüft installiert |

Der Artikel beschreibt 83 Serviceberichte (37 Inspektionen und 46 Reparaturberichte). Dies ist eine Publikationsangabe, keine von ServicePulse aus den 123 Dateien neu rekonstruierte Berichtszahl. Der Artikel nennt 42 gelabelte Einträge nach Ausschluss von vier Fällen ohne Daten. Die eigene Prüfung des Excel-Kalendertags findet 39 Tage mit Messpunkten; die Kriterien sind verschieden und werden nicht gleichgesetzt.

## Rekonstruktion der Autorenpipeline

1. Revco: monatliche `.dat`-Dateien mit variierenden Headern lesen, konkatenieren. Haier: SQLite-Tabellen `EACH_POINT_DATA_CHANGE`, `TEMPER_RECORD`, `EVENT_RECORD`, `WARNINGS_RECORD` auslesen.
2. Spalten umbenennen, Typen konvertieren, Zeitstempel sortieren; teils vollständige `dropna()`-Filter. Haier verbindet RTD mit Sensordaten über Zeilenposition, ohne Zeitjoin.
3. Geräteereignisse dem nächsten Messpunkt zuweisen: Revco-Schwelle 120 s, Haier 720 s. Mehrere Ereignisse als Listen zusammenfassen.
4. Konstanten Uhrenoffset `actual_time - internal_time` auf Temperaturzeitstempel addieren. Die separat gespeicherten Ereignisdateien werden in `data_pipeline.py` nicht mitkorrigiert.
5. Servicekalendertag auf 12 Uhr setzen, `FAULT_TWEAKS` addieren (im geprüften Stand Nullwerte), nächsten Messpunkt ohne maximale Distanz wählen, `main_fault` anfügen.
6. Speicherung über fastparquet; thermodynamische Kompressorleistungsberechnung in der Hauptpipeline auskommentiert. ServicePulse behandelt Spannung daher nicht als Leistungs- oder Energiemessung.

## Kritische Befunde und eigene Entscheidungen

- `RevcoTransformer.transform_temp`: `df.drop_duplicates(...)` wird weder zugewiesen noch `inplace` ausgeführt. Die veröffentlichte Temperaturbasis enthält tatsächlich 122 zusätzliche Zeilen mit bereits vorkommendem Zeitstempel, verteilt auf 14 Revco-Dateien. Diese Zeilen werden bei ServicePulse nicht heimlich gelöscht; Mittelwerte sind messpunktgewichtet und können davon beeinflusst sein.
- Pauschales `dropna()` kann nutzbare Teilmessungen entfernen. Eigene Leser behalten Teilwerte und berichten ungültige Felder.
- Nächster-Messpunkt-Zuordnung von Servicefällen ohne Distanzgrenze kann über große Lücken greifen. ServicePulse zeigt den Originalkalendertag und explizit leere Fenster, kein künstliches Label auf entfernten Messpunkten.
- Zeitkorrektur wird auf veröffentlichte Temperaturdaten nicht erneut angewandt. Separate Geräteereignisse werden mit dokumentiertem Offset verschoben. Keine Zeitzone oder historische Driftkorrektur ist verifiziert.
- Plot-Helfer referenzieren teilweise andere Namen als tatsächliche Parquet-Spalten bzw. Konstanten. ServicePulse liest das Dateischema, keine aus README-Beispielen erfundenen Felder.
- Gerätekennung stammt bei Parquets aus dem Dateinamen. Diese Zuordnung ist eine Autorenentscheidung und muss bei Widerspruch zum Rohdateikopf separat geprüft werden.
- Autorenlabel `main_fault` im Parquet bleibt Drittannotation. Excel-Zeilen sind die einzige Basis der Servicekennzahlen; Geräteereignisse werden nicht hinzugezählt.
- Artikel/Modellmetadaten enthalten unterschiedliche Kältemittelangaben für Haier. Keine thermodynamischen Berechnungen auf dieser unaufgelösten Grundlage. Primärdatenblatt klären, bevor Kältemittelmodelle verwendet werden.

## Gezielte Rohdatenprüfung

Revco-Stichprobe `data/raw_data/Revco/806018/temp/240365_tempdatalog_202210.dat`: 14.552 Zeilen, gültige Zeit- und RTD-Werte. Eigenes Einlesen plus dokumentierter Uhrenoffset reproduziert bei allen 14.552 Zeilen Zeitstempel und RTD der veröffentlichten Parquet-Datei (Toleranz 0,001 °C). Der Kopf nennt **Unit Name 806022**, obwohl der Quellordner **806018** heißt. Das ist ein ungeklärter Identitätskonflikt; rechnerische Reproduktion beweist keine physische Geräteidentität.

Haier-Stichprobe `data/raw_data/Haier/809169/lowtemperbox.db`: beide Tabellen enthalten je 88.582 Zeilen ohne doppelte TIME-Werte. An 2.132 Positionen unterscheiden sich die Zeitstempel. Eigene zeitbasierte Nearest-Zuordnung mit maximal 2 s Toleranz findet alle RTD-Werte bei maximal 1 s Abstand ohne Mehrfachverwendung. Das dokumentiert einen prüfbedürftigen Positionsjoin; es beweist für sich keine falsch zugeordneten RTD-Werte im publizierten Bestand. Die neue Stichprobe ersetzt die veröffentlichten Parquets nicht automatisch.

Eigene Leser: `servicepulse/raw.py`. Reproduzierbarer Stichprobenbericht: `data/processed/raw_sample_audit.json`, erzeugt durch `scripts/audit_samples.py`. Nur diese beiden Rohdateien wurden vollständig untersucht; der gesamte 8.600-Dateien-Rohbestand wurde nicht neu verarbeitet.

## Fehlerdokumentation und Quellenkonflikte

Gezielt gelesen wurden drei Servicefälle samt relevanter PDF-Seiten:

| Gerät/Fall | Befund | Entscheidung |
|---|---|---|
| 806030, 30.08.2022, SR49824-10000 | Excel: Water valve adjustment; CSV: Refrigerant leakage at stage 1. Bericht beschreibt Ventilanpassung und Firmwareaktualisierung; kein eindeutiger Beleg für den CSV-Leckagetext | Excel beibehalten, Textwiderspruch ausweisen |
| 806031, SR51059-10000 | Excel 03.02.2023; CSV 02.03.2023. PDF: Auftragsdatum 02.03., Startdatum 06.03., Lösung/Unterschrift 09.03.2023 | wahrscheinlicher Excel-Datumsfehler; keine automatische Änderung, da Auftrag, Reparatur und Fehlerbeginn verschiedene Zeitpunkte sind |
| 808783, 14.09.2021, SR47700 | Excel nennt Stage 1; CSV Stage 1 and 2. Bericht beschreibt Arbeiten an beiden Stufen, Auftrags- und Ausführungsdatum unterscheiden sich | Mehrkomponentenfall; Excel nicht stillschweigend erweitern |

Originale bleiben unter `research/samples/data/documentation/service_reports/Revco/`. Berichtspfad und Auftragsdatum allein belegen keinen Beginn des Defekts. Vollständige manuelle Durchsicht aller Serviceberichte bleibt offen. Keine persönlichen Kontaktdaten wurden in das Dashboard übernommen.
