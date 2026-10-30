# ServicePulse

Deutschsprachige lokale Verwaltung und Analyse von Kälteanlagen. Weiterentwicklung des bestehenden Praxisphasen-Prototyps; keine automatische Ausfallprognose.

## Start unter Windows

`start.cmd` doppelt anklicken oder `ServicePulse.code-workspace` in VS Code öffnen und F5 drücken. Der normale Start prüft PostgreSQL und die Schemaversion, anschließend startet das Dashboard auf http://127.0.0.1:8501 . Nur eine Dashboardinstanz auf diesem Port verwenden. Der Start führt keinen erneuten Import, keine Migration und kein Backup aus. Auf einem noch nicht vorbereiteten Rechner wird einmalig die Erstvorbereitung aufgerufen.

Auf diesem Laptop nutzt ServicePulse die vorhandenen PostgreSQL-17-Programme für eine eigene Instanz auf 127.0.0.1:55432. Docker ist nicht erforderlich. Der bereits vorhandene Windows-Dienst bleibt unverändert. Die Daten liegen dauerhaft unter `data/postgresql`; nach einem Rechnerneustart startet die Instanz beim nächsten ServicePulse-Start erneut.

Ein neuer Clone benötigt Python 3.13 und installierte PostgreSQL-Binärdateien (auf diesem Laptop PostgreSQL 17). Im Projektterminal:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/prepare_database.py
.\start.cmd
```

Die vorhandene `.venv` auf diesem Laptop weiterverwenden. Geheimnisse werden lokal erzeugt. Die großen Messdateien separat gemäß [Datenimport](docs/datenimport.md) beschaffen. Ohne Messdateien funktioniert die PostgreSQL-Serviceverwaltung, ohne PostgreSQL keine verdeckte Excel-Ersatzquelle.

## Vier Bereiche

- **Übersicht:** aktuelle Statistiken, Kategorien, Gerätehäufigkeiten, Wiederholungen, Zeitverteilung, Filter und CSV.
- **Geräte & Serviceberichte:** suchen, Geräte anlegen, Historie, ähnliche Fälle, Berichte erfassen und mit Änderungshistorie bearbeiten.
- **Betriebsanalyse & Vergleiche:** echte Parquet-Werte, Vorher/Nachher, Minima/Maxima, Messabdeckung und sichtbare Lücken. Drei belegte Forschungsfälle bleiben direkt auswählbar.
- **Datenqualität & Forschung:** Forschungsfrage, Kontrollen, Quellen und Einschränkungen; technische Tabellen in Expertenansichten.

## Daten und Technik

PostgreSQL ist die maßgebliche Servicequelle: 46 historische Einträge mit unveränderlichen Originalwerten, Datei-Prüfsumme, Blatt und Zeile. Neue Berichte sind als selbst erfasst gekennzeichnet. Änderungen erhalten Versionen und Protokolle; keine endgültige Löschfunktion.

106 unveränderte Parquets mit 181.309.902 Mess-/Meldungszeilen bleiben auf dem Datenträger. PostgreSQL enthält Dateimetadaten; DuckDB fragt begrenzte Zeitfenster direkt ab. Die frühere DuckDB-Servicekopie bleibt historische Prüfreferenz. SQLite wird nur zum Lesen originaler Haier-Rohdaten verwendet.

[Professor-Erklärung mit Architektur und Fünf-Minuten-Demo](docs/PROJEKT_ERKLAERUNG.md) · [Aktueller Code-Review und Testbericht](docs/ABSCHLUSSBERICHT_CODE_REVIEW.md) · [Start und Sicherung](docs/postgresql_windows.md) · [Dateien, Datenfluss und SQL](docs/postgresql_architektur.md) · [Fallprüfung 806279](docs/fall_806279_pruefung.md) · [Anforderungsstand](docs/professor_anforderungen.md)

## Bewusste Wartung

```powershell
# Erstvorbereitung; auf diesem Laptop bereits erledigt
.\.venv\Scripts\python.exe scripts/prepare_database.py
# Nur Server/Schemastand prüfen (wird vom Starter verwendet)
.\.venv\Scripts\python.exe scripts/prepare_database.py --start-only
# Vorhandene Migrationen bewusst anwenden
.\.venv\Scripts\python.exe scripts/prepare_database.py --migrate
# Excel-Import prüfen und neu hinzugefügte Messdateien registrieren
.\.venv\Scripts\python.exe scripts/prepare_database.py --sync
# Eigenständige Sicherung, beispielsweise nach eigenen Serviceeingaben
.\.venv\Scripts\python.exe scripts/prepare_database.py --backup
```

Migration und Synchronisation gehören zur Vorbereitung, nicht zum Vortrag. Originale werden nicht überschrieben; ein geänderter bereits importierter Excel-Bestand wird abgewiesen. Normale Starts erstellen keine neuen Sicherungen. Dumps und Originaldateien zusätzlich extern sichern.

## Prüfen

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q --cov --cov-report=term-missing --cov-report=xml --junitxml=docs/testlauf_review.xml
.\.venv\Scripts\python.exe scripts/check_local.py
```

Schreibtests verwenden eine eigene kurzlebige PostgreSQL-Instanz auf einem freien Port, einschließlich ihrer Neustarts und einer Wiederherstellung in einer zweiten Testdatenbank. Die Nutzinstanz wird dafür nicht neu gestartet. `local_data` kennzeichnet Tests mit optionalen Forschungsdateien; fehlende Dateien werden mit konkretem Grund gemeldet. `pytest -m "not local_data"` wählt die unabhängige Gruppe. `check_local.py` benötigt den vollständigen lokalen Bestand einschließlich der historischen DuckDB-Prüfreferenz.

GitHub Actions nutzt einen Windows-Runner mit nativen PostgreSQL-Programmen, frisch erzeugten Testzugängen und `SERVICEPULSE_CI=1`. Dadurch laufen auch normale Oberflächentests gegen einen separaten Excel-Demobestand. Es werden weder lokale Geheimnisse noch die großen Parquet-Dateien benötigt. Test- und Coverage-Berichte werden als Workflow-Artefakte gespeichert; keine feste Coverage-Grenze ist gesetzt.

`requirements.txt` nennt direkte Laufzeitabhängigkeiten, `requirements-dev.txt` zusätzlich Ruff und pytest-cov, `requirements-lock.txt` die getesteten Versionen als Constraints. Datenbanken, Backups, Kennwörter, `.env`, `.venv`, Forschungsreferenzen und große Messdateien sind aus Git ausgeschlossen.
