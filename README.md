# ServicePulse

Deutschsprachige lokale Verwaltung und Analyse von Kälteanlagen. Weiterentwicklung des bestehenden Praxisphasen-Prototyps; keine automatische Ausfallprognose.

## Start unter Windows

`start.cmd` doppelt anklicken oder `ServicePulse.code-workspace` in VS Code öffnen und F5 drücken. PostgreSQL wird vorbereitet, anschließend das Dashboard unter http://127.0.0.1:8501 gestartet. Keine manuelle SQL-Bedienung nötig.

Auf diesem Laptop nutzt ServicePulse die vorhandenen PostgreSQL-17-Programme für eine eigene Instanz auf 127.0.0.1:55432. Docker ist nicht erforderlich. Der bereits vorhandene Windows-Dienst bleibt unverändert. Die Daten liegen dauerhaft unter `data/postgresql`; nach einem Rechnerneustart startet die Instanz beim nächsten ServicePulse-Start erneut.

Ein neuer Clone benötigt Python, installierte PostgreSQL-Binärdateien, eine virtuelle Umgebung und `pip install -r requirements.txt`. Danach `start.cmd` verwenden. Geheimnisse werden lokal erzeugt. Die großen Messdateien separat gemäß [Datenimport](docs/datenimport.md) beschaffen. Ohne Messdateien funktioniert die PostgreSQL-Serviceverwaltung, ohne PostgreSQL keine verdeckte Excel-Ersatzquelle.

## Vier Bereiche

- **Übersicht:** aktuelle Statistiken, Kategorien, Gerätehäufigkeiten, Wiederholungen, Zeitverteilung, Filter und CSV.
- **Geräte & Serviceberichte:** suchen, Geräte anlegen, Historie, ähnliche Fälle, Berichte erfassen und mit Änderungshistorie bearbeiten.
- **Betriebsanalyse & Vergleiche:** echte Parquet-Werte, Vorher/Nachher, Minima/Maxima, Messabdeckung und sichtbare Lücken. Drei belegte Forschungsfälle bleiben direkt auswählbar.
- **Datenqualität & Forschung:** Forschungsfrage, Kontrollen, Quellen und Einschränkungen; technische Tabellen in Expertenansichten.

## Daten und Technik

PostgreSQL ist die maßgebliche Servicequelle: 46 historische Einträge mit unveränderlichen Originalwerten, Datei-Prüfsumme, Blatt und Zeile. Neue Berichte sind als selbst erfasst gekennzeichnet. Änderungen erhalten Versionen und Protokolle; keine endgültige Löschfunktion.

106 unveränderte Parquets mit 181.309.902 Mess-/Meldungszeilen bleiben auf dem Datenträger. PostgreSQL enthält Dateimetadaten; DuckDB fragt begrenzte Zeitfenster direkt ab. Die frühere DuckDB-Servicekopie bleibt historische Prüfreferenz. SQLite wird nur zum Lesen originaler Haier-Rohdaten verwendet.

[Start und Sicherung](docs/postgresql_windows.md) · [Dateien, Datenfluss und SQL](docs/postgresql_architektur.md) · [Testbericht](docs/postgresql_testbericht.md) · [Fallprüfung 806279](docs/fall_806279_pruefung.md) · [Demo am 03.11.](docs/praxis_demo_03_11.md) · [Anforderungsstand](docs/professor_anforderungen.md)

## Prüfen

```powershell
.\.venv\Scripts\python.exe scripts/prepare_database.py
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/testlauf_postgresql.xml
.\.venv\Scripts\python.exe scripts/check_local.py
```

Schreibtests verwenden getrennte kurzlebige PostgreSQL-Testdatenbanken. Ein Test startet die eigene PostgreSQL-Instanz neu; währenddessen keine manuellen Berichte bearbeiten. Der Nutzbestand bleibt frei von Testberichten.

`requirements.txt` nennt direkte Abhängigkeiten, `requirements-lock.txt` die getesteten Versionsgrenzen. Datenbanken, Backups, Kennwörter, `.env`, `.venv`, Forschungsreferenzen und große Messdateien sind aus Git ausgeschlossen.
