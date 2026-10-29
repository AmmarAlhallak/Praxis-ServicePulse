# ServicePulse

Lokales Analyse-Dashboard für historische ULT-Betriebsdaten und dokumentierte Serviceeinträge. Erstellt am 29.10.2026 für die Praxisphase. Keine Prognose und keine automatische Interpretation von Serviceeinträgen als unabhängige Ausfälle.

## GitHub-Version: Praxis-ServicePulse

Dieses Repository enthält eigenen Quellcode, Tests, Dokumentation und die kleine wissenschaftliche Service-Excel. Die rund 6 GB großen Parquets, Forschungsreferenzkopien, die erzeugte DuckDB und `.venv` werden nicht mit Git versioniert. Die nachfolgenden Bestandszahlen beschreiben den geprüften lokalen Entwicklungsbestand, nicht den Umfang eines frischen Git-Clones.

Ein frischer Checkout startet nach Installation mit der enthaltenen Excel. Für Messkurven die Schritte in [datenimport.md](docs/datenimport.md) ausführen; für die Autorenmetadaten zunächst `scripts/inspect_repository.py`. Danach `scripts/build.py` ausführen. Tests, die ausdrücklich optionale lokale Messdateien oder den Build benötigen, werden ohne diese Dateien übersprungen; die Excel- und Basistests laufen weiterhin. Lokale maschinenspezifische Prüfprotokolle sind ebenfalls aus Git ausgeschlossen.

## Windows: Installation und Start

Für Visual Studio Code ist `ServicePulse.code-workspace` eingerichtet: öffnen, lokale `.venv` wählen und **F5 → ServicePulse: Dashboard (Streamlit)** starten. Alternativ `start.cmd` verwenden. Vollständige [Windows-/VS-Code-Anleitung](docs/windows_vscode.md), [Dateien und SQL erklärt](docs/technik_sql.md), [technische Demo am 03.11.](docs/vscode_demo_03_11.md).

Im Projektverzeichnis in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Die virtuelle Umgebung und Abhängigkeiten sind in diesem Arbeitsverzeichnis bereits installiert. Direkter Start ohne Aktivierung:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Alternativ `./start.ps1`, sofern die lokale PowerShell-Ausführungsrichtlinie dies erlaubt. Aufruf ohne Aktivierung vermeidet Änderungen der Ausführungsrichtlinie. Browser: <http://127.0.0.1:8501>. Beenden: Strg+C im Terminal. Python 3.13.7 wurde hier geprüft; Lockdatei `requirements.txt` enthält die tatsächlich installierten App-/Testabhängigkeiten. Separate optionale PDF-Prüfwerkzeuge sind nicht für den App-Start erforderlich.

## Daten und Herkunft

- Lokale `fault_summary_R1.xlsx`: 46 Einträge, 24 Geräte; erstes Datenblatt inhaltlich identisch mit dem GitLab-Exemplar.
- 106 veröffentlichte Parquet-Dateien für 38 Revco- und 15 Haier-Geräte sind heruntergeladen: 6.013.873.936 Bytes, zusammen 181.309.902 Zeilen einschließlich Geräteereignissen.
- [Artikel Huang et al. (2023)](https://doi.org/10.1038/s41597-023-02808-6), [Datensammlung](https://doi.org/10.6084/m9.figshare.c.6805332.v1), [Autorencode](https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data).
- GitLab-Stand: `2779f6043fd9d3a7e1b8b1fe0c0f857735684b69`. Die Dateien sind veröffentlichte, bereits durch die Autoren verarbeitete Daten. Eigene Rohdatenleser wurden an zwei Stichproben geprüft, nicht am gesamten Rohbestand neu ausgeführt.

Lizenzen, Geräteidentitätskonflikte und Abweichungen der Quellen: [Herkunft](docs/lizenzen_herkunft.md), [Repositoryprüfung](docs/repository_pruefung.md), [Ergebnisse](docs/datenanalyse.md). Wissenschaftliche Definitionen und Grenzen sind Bestandteil des Dashboards.

## Funktionen

Übersicht, Originalkategorien und zusammengefasste Kategorien, Geräteanalyse, zeitliche Verteilung, reale Temperatur-/Spannungsreihen, aggregierte Minima/Mittelwerte/Maxima, markierte Servicetage, begrenzte Geräteereignisabfragen mit Uhrkorrektur, messpunktgewichtete Vorher/Nachher-Statistik, Qualitätskontrolle, Quellenansicht, CSV-Export und Parquet-Upload. Messgerät kann unabhängig vom Servicefilter gewählt werden; markiert werden ausschließlich ausgewählte Serviceeinträge. Der Bitcode `State` bleibt in den Quelldaten erhalten und wird nicht als kontinuierliche Messgröße gemittelt.

Ohne Parquet funktioniert die Excel-Analyse vollständig. Import größerer Dateien durch Kopieren nach `data/raw/<Modell>/`; Upload bis 300 MB. [Genaue Anleitung](docs/datenimport.md).

## Struktur und Architektur

```text
app.py                       Streamlit und Plotly
servicepulse/
  faults.py                  Excel-Erkennung, Normalisierung, Filter, Kennzahlen
  measurements.py            Parquet-Metadaten, DuckDB-Fensterabfragen, Uhrenoffsets
  raw.py                     eigene kontrollierte Rohdatenleser
  storage.py                 DuckDB-Tabellen und SQL-Views
scripts/
  inspect_repository.py      vollständiger GitLab-Baum und Referenzdateien
  download_data.py           selektiver Download veröffentlichter Parquets
  build.py                   Aufbereitung und vollständige Dateiqualitätsprüfung
  check_local.py             schreibgeschützter Excel-/DuckDB-/Dateiabgleich
  fetch_samples.py           ausgewählte Rohdaten und Serviceberichte
  fetch_article.py           geprüften Artikelvolltext sichern
  audit_samples.py           Stichprobenprüfung und Servicefenster-Abdeckung
data/raw/{Revco,Haier}/        unveränderte veröffentlichte Parquets
data/processed/               DuckDB, normalisierte Einträge, Prüfberichte
research/reference/           separater, nicht ausgeführter Autorencode und CSVs
research/samples/             gezielt geprüfte Rohdateien und Serviceberichte
research/*.json               Quellmetadaten, Commit, Dateibaum, Downloadmanifest
tests/                        automatisierte Fach- und App-Tests
docs/                         Methodik, Forschung, Literatur, Planung und Demo
.vscode/                     lokale Umgebung, F5 und Aufgaben
ServicePulse.code-workspace   Projekt in VS Code öffnen
start.cmd                    Windows-Start ohne Umgebungsaktivierung
```

`faults.parquet` enthält Originalspalten plus abgeleitete Felder mit Zeilenherkunft. `servicepulse.duckdb` enthält `faults`, `measurement_files`, `quality_checks` sowie `category_counts` und `repeated_categories`. Die App liest die kleine Excel direkt; DuckDB erzeugt messgrößen- und zeitlich begrenzte SQL-Abfragen gegen externe Parquets. Große Messreihen werden nicht in die Datenbank kopiert. CSV-/Parquet-Qualitätsberichte sind reproduzierbare Ergebnisse des Builds.

## Reproduktion und Tests

```powershell
.\.venv\Scripts\python.exe scripts/build.py
.\.venv\Scripts\python.exe scripts/audit_samples.py
.\.venv\Scripts\python.exe scripts/check_local.py
.\.venv\Scripts\python.exe -m pytest -q
```

Der Build prüft alle 106 Messdateien vollständig, einschließlich Zeitstempel, RTD-Nullwerte, Extremwerte und Messlücken. `audit_samples.py` benötigt die bereits heruntergeladenen Stichproben und veröffentlichten Parquets. Frischer Download: zuerst `inspect_repository.py`, danach `download_data.py`, optional `fetch_samples.py`; alle Skripte aus dem Projektverzeichnis starten. Netzfehler/Fehldownloads sind im Manifest zu prüfen. `research/` und `data/` werden wegen Umfang und Drittmaterial nicht in Git aufgenommen. Die lokale Excel bleibt unverändert.

`check_local.py` ist ein schneller schreibgeschützter Abgleich der aktuellen Excel mit DuckDB-Tabellen/Views und der Parquet-Dateiliste. SQLite wird ausschließlich zum Lesen originaler Haier-Rohdaten verwendet; DuckDB bleibt die Anwendungsdatenbank. Das Dashboard liest die aktuelle kleine Excel direkt und verwendet DuckDB für die großen externen Parquet-Abfragen.

## Für den Termin

[Demo am 03.11.2026](docs/demo_03_11.md), [Projektstatus](docs/projektstatus.md), [Zeitplan](docs/zeitplan.md), [Forschungsfrage](docs/forschungsfrage.md), [Literatur](docs/literatur.md).
