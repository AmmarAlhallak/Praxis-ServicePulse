# ServicePulse selbst öffnen – Anleitung für den Professorentermin

Geprüft am 30.10.2026 nach deinem Neustart. Arbeitsordner: `C:\Users\ammar\Downloads\fault_summary_R1`.

Heute tatsächlich geöffnet: VS-Code-Arbeitsbereich samt dieser Anleitung, pgAdmin 4 **9.19** und das Dashboard. `start.cmd` hat PostgreSQL **17.6** auf Port 55432 und Streamlit auf Port 8501 gestartet. Der erneute Start hat null neue historische Berichte und null neue Messdateien importiert. Die Datenbankabfrage bestätigt 53 Geräte, 46 Berichte und 106 Messdateien. In pgAdmin ist `public.service_reports` mit „All Rows“ geöffnet: **Total rows: 46**. Daten wurden dabei nur gelesen.

## 1. Anwendung starten

1. Im Datei-Explorer den Arbeitsordner öffnen.
2. **`start.cmd` doppelt anklicken.** Das startet zuerst die eigene PostgreSQL-Instanz und danach das Dashboard. Die Meldung „PostgreSQL bereit“ abwarten. Das Startfenster während der Vorführung geöffnet lassen.
3. Im Browser **http://127.0.0.1:8501/** eingeben.
4. In der Übersicht sind derzeit 46 Serviceeinträge, 24 betroffene Geräte, 11 mehrfach dokumentierte Geräte und 5 wiederholte Gerät/Kategorie-Paare sichtbar; insgesamt sind 53 Geräte registriert.

Es gibt zwei alternative Startwege: `start.cmd` oder VS Code mit F5. Nur **einen** davon für dieselbe Vorführung verwenden, sonst ist Port 8501 bereits belegt.

## 2. Code in Visual Studio Code zeigen

1. Im Projektordner **`ServicePulse.code-workspace`** mit VS Code öffnen. Falls Doppelklick nicht VS Code startet: VS Code → Datei → Arbeitsbereich aus Datei öffnen.
2. Links im Explorer siehst du die vorhandenen Projektdateien.
3. Geeignete Dateien zum Erklären:

| Datei | Was du zeigen kannst |
|---|---|
| `app.py` | Die vier Bereiche des Dashboards und die Analysebedienung |
| `servicepulse/models.py` | Tabellen und Beziehungen der PostgreSQL-Datenbank |
| `servicepulse/repository.py` | Historischer Import, Laden und Speichern von Berichten |
| `servicepulse/management.py` | Geräte- und Berichtformulare |
| `servicepulse/measurements.py` | DuckDB-Abfragen der Parquet-Messwerte |
| `docs/postgresql_architektur.md` | Verständliche Erklärung des gesamten Datenflusses |

Falls die Anwendung noch nicht über `start.cmd` läuft, kannst du stattdessen F5 → **ServicePulse: Dashboard (Streamlit)** verwenden. Der Vorbereitungstask startet PostgreSQL. Für den jetzigen Öffnungsvorgang wurde tatsächlich `start.cmd` ausgeführt und VS Code zusätzlich zur Codeansicht geöffnet.

## 3. Die Datenbank in pgAdmin öffnen

1. Im Windows-Startmenü **pgAdmin 4** öffnen. Die aktuelle Version liegt unter `C:\Users\ammar\AppData\Local\Programs\pgAdmin 4\runtime\pgAdmin4.exe` und wurde als **9.19** geprüft. Die ältere mit PostgreSQL gebündelte Kopie 9.6 liegt weiterhin unter `C:\Program Files\PostgreSQL\17\pgAdmin 4`; für die Vorführung die neue Kopie verwenden.
2. Links im **Object Explorer** die Gruppe **ServicePulse** aufklappen.
3. **ServicePulse (lokal)** öffnen. Diese Verbindung zeigt auf `127.0.0.1`, Port **55432**, Datenbank **servicepulse**, Benutzer **servicepulse_app**.
4. Den Pfad **Databases → servicepulse → Schemas → public → Tables** aufklappen. Falls „Schemas“ weiter unten steht, im linken Baum nach unten scrollen.
5. Wichtige Tabellen:

| Tabelle | Inhalt |
|---|---|
| `devices` | Registrierte Geräte |
| `service_reports` | Historische und selbst erfasste Serviceberichte |
| `categories` | Fehlerkategorien |
| `service_actions` | Reparatur-/Wartungsmaßnahmen |
| `sources` | Herkunft der Einträge und Dateien |
| `measurement_files` | Metadaten und Speicherorte der Messdateien |
| `audit_log` | Versionierte Änderungshistorie |

6. Beispielsweise Rechtsklick auf **service_reports → View/Edit Data → All Rows**. Für die Vorführung Daten nur ansehen; neue Berichte bequem im Dashboard erfassen.

Die heute darüber ausgeführte Abfrage lautet:

```sql
SELECT * FROM public.service_reports
ORDER BY id ASC;
```

Die vorhandene Gruppe **Servers → PostgreSQL 17** gehört zu deinem anderen lokalen PostgreSQL-Dienst. Für ServicePulse die eigene Gruppe **ServicePulse** und den Port **55432** verwenden.

## 4. Wo liegen die Daten wirklich?

Alle folgenden Speicherorte liegen auf deinem Laptop, unter dem Arbeitsordner:

| Speicherort | Bedeutung |
|---|---|
| `data/postgresql/` | Physischer Datenbestand der eigenen PostgreSQL-Instanz. Enthält unter anderem Geräte, Berichte und Audit. PostgreSQL verwaltet viele interne Dateien; diese nicht manuell bearbeiten. |
| `data/raw/Revco/` und `data/raw/Haier/` | Veröffentlichte Parquet-Mess- und Ereignisdateien. Große Zeitreihen bleiben hier. |
| `fault_summary_R1.xlsx` | Unveränderte historische Excel-Referenz der 46 importierten Einträge. Neue Berichte werden in PostgreSQL gespeichert. |
| `data/processed/servicepulse.duckdb` | Frühere abgeleitete Datenbank als historische Prüfreferenz. Keine operative Quelle neuer Serviceberichte. |
| `data/backups/postgresql/` | Logische PostgreSQL-Sicherungen im Dump-Format, beim erfolgreichen Start erzeugt. |
| `data/backups/before_postgresql_20261030/` | Sicherung vor der Umstellung: Excel, frühere DuckDB, Git-Bundle und Original-Prüfsummen. |
| `data/private/` und `.env` | Lokale Verbindungseinstellungen und Geheimnisse. Nicht beim Professor aufblenden und nicht veröffentlichen. |

**pgAdmin ist nur das Verwaltungsfenster. Die eigentlichen ServicePulse-Daten liegen in PostgreSQL unter `data/postgresql/`, nicht im pgAdmin-Programmordner.**

## 5. Eine kurze Vorführung

1. **Übersicht:** 46 historische Berichte und die Kennzahlen zeigen.
2. **Geräte & Serviceberichte:** Gerät **806279** suchen, seine drei bisherigen Berichte zeigen und die Erfassungsmaske erläutern. Ohne tatsächlich neuen Bericht nichts zu Demonstrationszwecken in den Forschungsbestand schreiben.
3. **Betriebsanalyse & Vergleiche → Beispiel: Temperaturveränderung:** Servicetag 28.06.2022, RTD und je sieben Tage. Lücke und warme Werte zeigen. Eine beobachtete Temperaturänderung beweist keine Reparaturwirkung.
4. **Datenqualität & Forschung:** Grenzen und Quellen zeigen.
5. In pgAdmin die Tabelle `service_reports` und in VS Code `models.py`/`repository.py` zeigen.

Ein Satz zur Architektur: „PostgreSQL speichert Geräte, Serviceberichte und ihre Änderungen dauerhaft. Die großen Messreihen bleiben in Parquet-Dateien und werden mit DuckDB gezielt abgefragt. Streamlit bildet die Benutzeroberfläche.“

Für den ausführlicheren Ablauf: [Praxis-Demo](praxis_demo_03_11.md). Technische Details: [Architektur](postgresql_architektur.md). Prüfstand: [Testbericht](postgresql_testbericht.md).
