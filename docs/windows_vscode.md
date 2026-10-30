# ServicePulse unter Windows in Visual Studio Code

**Aktuell seit 30.10.2026:** PostgreSQL ist die operative Servicequelle; vier Hauptbereiche. [Startanleitung](postgresql_windows.md) und [Architektur](postgresql_architektur.md). Die folgenden früheren Details bleiben als Entwicklungshistorie erhalten; der direkte Excel-App-Start ist abgelöst.


Arbeitsordner: `C:\Users\ammar\Downloads\fault_summary_R1`. Der bestehende Code, die Excel-Datei, Parquets und DuckDB bleiben die Grundlage. Es wurde kein zweites Projekt angelegt.

## Öffnen, bearbeiten und starten

1. In VS Code **Datei → Arbeitsbereich aus Datei öffnen** wählen und `ServicePulse.code-workspace` im Projektordner öffnen. Alternativ den gesamten Ordner öffnen, nicht nur `app.py`.
2. Die Microsoft-Erweiterungen Python, Python Debugger und Pylance sind installiert. Falls die Interpreterauswahl nicht stimmt: `Strg+Umschalt+P` → **Python: Interpreter auswählen** → `.venv (3.13.7)` bzw. `C:\Users\ammar\Downloads\fault_summary_R1\.venv\Scripts\python.exe` auswählen.
3. **F5** drücken und bei Bedarf **ServicePulse: Dashboard (Streamlit)** wählen. Ausgabe erscheint in der Debugging-Konsole. Browser selbst unter <http://127.0.0.1:8501> öffnen. Die lokale Streamlit-Konfiguration unterdrückt die Erststart-E-Mail-Abfrage und automatisches Browseröffnen.
4. Beenden mit **Umschalt+F5** oder der roten Stopptaste. Änderungen an Python-Dateien speichern; im Dashboard bei Bedarf **Rerun** wählen.

Alle Dateien bleiben lokal und editierbar. `data/` und `research/` sind lediglich aus der VS-Code-Textsuche ausgeschlossen, damit eine Suche nicht die großen Datenbestände durchsucht. Im Datei-Explorer bleiben sie sichtbar. Excel und Parquet sind binäre Datenformate; Python-Code, SQL-Erklärungen, JSON-Konfigurationen und Markdown-Dokumente können direkt bearbeitet werden. Die Original-Excel nicht im Editor als Text verändern.

Die Schaltfläche **Run Python File** oder die vorhandene Code-Runner-Erweiterung startet `app.py` nicht korrekt als Streamlit-App. Verwende die eingerichtete F5-Konfiguration oder die folgenden Befehle.

## Start ohne Debugger

In einem VS-Code-Terminal im Projektordner:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Oder `start.cmd` doppelt anklicken bzw. im Terminal `./start.cmd` aufrufen. Die CMD-Datei wechselt selbst in den Projektordner und benötigt keine Aktivierung der virtuellen Umgebung. `start.ps1` bleibt ebenfalls vorhanden; bei blockierter PowerShell-Ausführungsrichtlinie die CMD-Datei oder den direkten Python-Aufruf verwenden. Keine systemweite Richtlinienänderung nötig.

Nur eine Instanz auf Port 8501 starten. Wenn bereits eine läuft, diese weiterverwenden oder zuerst in ihrem Terminal mit Strg+C bzw. in VS Code mit Umschalt+F5 beenden. Für eine bewusst zweite Instanz: `./start.cmd --server.port 8502`, dann <http://127.0.0.1:8502> verwenden.

## Python-Umgebung

Die vorhandene `.venv` verwendet Python 3.13.7 (64 Bit). Alle App- und Testabhängigkeiten aus `requirements.txt` sind vorhanden. `pip check` wurde ausgeführt. Die Umgebung wird in VS-Code-Aufgaben und F5 explizit über ihren vollständigen Projektpfad angesprochen; eine Shell-Aktivierung ist nicht erforderlich.

Nur wenn die Umgebung später fehlt oder auf einen anderen Rechner übertragen wird:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Eine vorhandene funktionierende Umgebung muss dafür nicht neu erstellt werden. Virtuelle Umgebungen nicht zwischen Rechnern kopieren; auf dem Zielrechner mit den Anforderungen neu erstellen. Die optional für frühere PDF-Sichtung installierten Pakete sind keine Voraussetzung für App und Tests.

## Prüfen und Daten aktualisieren

```powershell
.\.venv\Scripts\python.exe scripts/check_local.py
.\.venv\Scripts\python.exe -m pytest -q
```

`check_local.py` vergleicht Excel-Inhalte, aktuelle Parquet-Metadaten, persistierte DuckDB-Tabellen und SQL-Views. Es arbeitet schreibgeschützt und ohne Netzwerk. Bei einem Unterschied meldet es einen Fehler und baut nichts ungefragt neu auf.

Nach bewusster Änderung der Excel oder des lokalen Parquet-Bestands:

```powershell
.\.venv\Scripts\python.exe scripts/build.py
```

Das aktualisiert abgeleitete Dateien in `data/processed/` und prüft die Messdateien vollständig. Originalquellen werden nicht geändert. Danach bei Bedarf `scripts/audit_samples.py` ausführen, um die Vorher-/Nachher-Abdeckung neu zu berechnen; dafür sind die bereits vorhandenen Stichproben und alle benötigten Messdateien erforderlich. Qualitäts-/Abdeckungsberichte sind Build-Ergebnisse und werden nicht bei jedem Dashboard-Filter neu berechnet.

In VS Code sind dieselben Befehle unter **Terminal → Aufgabe ausführen** hinterlegt: Dashboard starten, alle Tests, lokalen Datenstand prüfen, Datenbank/Qualitätsberichte aktualisieren. Test Explorer verwendet pytest. Der F5-Start wurde im echten VS-Code-Fenster geprüft; die Aufgaben verwenden dieselbe geprüfte Umgebung, wurden aber nicht zusätzlich alle über ihre Menüs angeklickt.

Technischer Überblick einschließlich tatsächlicher SQL-Abfragen: [technik_sql.md](technik_sql.md). Kurze Vorführung für den 03.11.: [vscode_demo_03_11.md](vscode_demo_03_11.md).
