# Prüfprotokoll Windows / VS Code

Prüfung am 29.10.2026 im bestehenden Projektordner auf diesem Windows-Laptop. Kein Neuaufbau des Projekts und kein Austausch der Originaldaten.

## Tatsächlich ausgeführt

| Prüfung | Nachweis / Ergebnis |
|---|---|
| Vorhandener Code und Struktur | `app.py`, alle eigenen Module und Skripte, Tests, Anforderungen, Startdatei und Streamlit-Konfiguration gelesen; vorhandene Daten-/Referenzordner inventarisiert |
| Python-Umgebung | vorhandene `.venv`, Python 3.13.7 64 Bit; `python -m pip check`: `No broken requirements found.` |
| Syntax | `python -m compileall -q app.py servicepulse scripts tests`: Exitcode 0 |
| VS Code | installiert, CLI-Version 1.127.0; Arbeitsbereich im echten Fenster geöffnet, `app.py` sichtbar/editierbar |
| Erweiterungen | Microsoft Python 2026.10.0, Debugger 2026.6.0, Pylance 2026.4.1 und Python Environments 1.40.0 über die VS-Code-CLI installiert |
| F5-Start | tatsächlicher Start mit `ServicePulse: Dashboard (Streamlit)` im VS-Code-Fenster; Debugging-Konsole meldet Server auf `127.0.0.1:8501`; HTTP-Healthcheck `ok` |
| Alternative Startdatei | `start.cmd --server.port 8502` aus `C:\Users\ammar\Downloads` statt dem Projektordner ausgeführt; Server und Healthcheck erfolgreich, Testinstanz anschließend gezielt beendet |
| Laufende App | anschließend weiter über den VS-Code-Debugger auf Port 8501 verfügbar; Browserübersicht mit 46/24/11/5 kontrolliert |
| Datenbank | vorhandene DuckDB schreibgeschützt geöffnet, alle 3 Tabellen und 2 Views abgefragt; vollständige Serviceinhalte, Qualitätskontrollen und Dateimetadaten gegen aktuelle Quellen verglichen |
| Reale Messwerte | SQL-Stundenaggregate für 806279 am 29.06.2022 gegen separat mit pandas berechnete Mittelwerte/Minima/Maxima/Anzahlen geprüft |
| Vollständige Parquet-Qualitätsprüfung | `scripts/build.py` erneut aus einem anderen Arbeitsordner ausgeführt; alle 106 Dateien geprüft, `errors.json` leer, DuckDB und abgeleitete Berichte erfolgreich aktualisiert |
| Paketversionen | alle 44 Einträge aus `requirements.txt` gegen die tatsächlich installierten Versionen abgeglichen; keine Abweichung |
| Gesamte Tests | **20 bestanden in 18,62 s**, keine fehlgeschlagenen oder übersprungenen Tests im abschließenden Lauf; Textausgabe `testlauf_windows.txt`, JUnit-Datei `testlauf_windows.xml` |

Details des schreibgeschützten Datenabgleichs: `lokale_pruefung.json`. JUnit und Textausgabe stammen vom tatsächlich ausgeführten abschließenden pytest-Lauf. Ein früherer neuer Kombinationstest schlug fehl; er wurde nicht als Erfolg gezählt.

## Gefundene und behobene Probleme

1. **Diagramm-ID-Kollision:** Bei einer Auswahl, die in Übersicht und Kategorietab dieselbe Grafik erzeugt, kollidierten automatisch erzeugte Streamlit-IDs. Alle fünf Diagrammstellen erhalten nun feste, eindeutige Schlüssel. Regressionstest kombiniert Gerät 806279, Refrigerant leakage und 28.06.2022, prüft Kennzahlen, Geräteanalyse, Diagramme, Servicemarkierung und Filterreset.
2. **Freie Haier-Ansicht außerhalb des Datenbestands:** Der bisher feste April-2023-Standard lag nach dem letzten Haier-Messdatum. Standardzeitraum wird jetzt aus tatsächlichen Zeitgrenzen der gewählten Datei bestimmt. Der reale Haier-Gerätewechsel wird getestet.
3. **Ungeeignetes Mitteln des Zustands-Bitcodes:** `State` wurde wie eine kontinuierliche Messgröße angeboten. Er bleibt unverändert in der Quelle, ist aber aus der Mittelwertauswahl und der Prüfung geeigneter Messgrößen ausgeschlossen.
4. **VS-Code-Interpreterauswahl:** Nach Erstinstallation wurde zeitweise ein ungültiger bzw. globaler Interpreter angezeigt. Vorhandene `.venv` wurde im aktiven Projekt ausgewählt. F5 und Aufgaben referenzieren zusätzlich ausdrücklich den projektlokalen Python-Pfad.
5. **Streamlit-Erstabfrage:** Der erste Debuggerstart traf auf die E-Mail-Abfrage des interaktiven Streamlit-Erststarts. Projektlokales `server.headless = true` verhindert diese Blockade; Browseradresse wird manuell geöffnet. Keine E-Mail wurde eingegeben.

## Prüfgrenzen

Die VS-Code-Aufgaben wurden konfiguriert und ihre Befehle/JSON geprüft; nicht jede Aufgabe wurde zusätzlich über das Menü gestartet. F5 und CMD-Start wurden tatsächlich ausgeführt. Der Test Explorer ist eingerichtet, die gesamte Testsuite wurde über denselben lokalen Interpreter in der Shell ausgeführt. Eine Installation auf einem zweiten Rechner oder eine Neuinstallation der bestehenden `.venv` wurde nicht durchgeführt.

Der Editor zeigt für die geöffnete `app.py` nach Auswahl der `.venv` keine Probleme mehr. Eine bereits vorher installierte, optionale **VS IntelliCode**-Erweiterung meldete beim Aktivieren ihrer Python-Unterstützung einen Fehler. Sie wurde nicht entfernt oder umkonfiguriert; Standard-Python, Pylance, Debugger und Dashboard funktionieren trotzdem. Die optionale IntelliCode-Vervollständigung ist damit nicht als funktionsfähig bestätigt. Screenshot des tatsächlichen F5-Starts samt `.venv`-Status: `vscode_start.png`.

Die Prüfung belegt technische Funktionsfähigkeit mit den vorhandenen Quellen. Sie bestätigt keine unabhängigen Ausfälle, keine physische Geräteidentität bei bekannten Quellenwidersprüchen und keinen exakten Fehlerbeginn. Offene fachliche Fragen aus `projektstatus.md` bestehen fort. Ein vollständiger neuer Netzwerkdownload war nicht erforderlich und wurde in dieser Prüfung nicht vorgenommen.
