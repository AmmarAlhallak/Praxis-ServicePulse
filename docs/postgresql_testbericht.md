# Prüfbericht der PostgreSQL-Weiterentwicklung

Ausgeführt am 30.10.2026 auf dem vorhandenen Windows-Laptop, Python-Umgebung des bestehenden Projekts. Kein neuer Projektordner. Entwicklungsbranch: `development/postgresql-service-management`.

## Nachgewiesene Ergebnisse

- Vollständiger letzter Lauf: **45 Tests bestanden, 0 fehlgeschlagen, 0 übersprungen, 50,26 Sekunden**. Ausgabe: [testlauf_postgresql.txt](testlauf_postgresql.txt). Maschinenbezogenes JUnit-Protokoll liegt lokal unter `docs/testlauf_postgresql.xml` und ist aus Git ausgeschlossen.
- Die bisherigen 35 Prüfungen bleiben enthalten; an die neue Architektur angepasst sind die erwarteten vier Bereiche und die Prüfung der Serviceverwaltung ohne Messdateien. Zehn zusätzliche Prüfungen betreffen PostgreSQL und die Fallnachprüfung.
- Alembic-Schema in einer echten separaten PostgreSQL-Testdatenbank aufgebaut. Wiederholter Excel-Import erzeugt keine Duplikate. Alle ursprünglichen Spalten und Werte der 46 Zeilen stimmen im erhaltenen PostgreSQL-Originalinhalt mit Excel überein.
- Kennzahlen unverändert: **46 Einträge, 24 betroffene Geräte, 11 Geräte mit mehreren Einträgen, 5 wiederholte Gerät/Kategorie-Paare**. **53 Geräte, 106 Messdateien, 181.309.902 Mess-/Meldungszeilen** registriert.
- Neue Berichte, unvollständige Angaben und neue Geräte ohne Messdaten getestet. Erneute gleiche Anforderung legt keinen zweiten Bericht an. Neue Verbindungen lesen gespeicherte Berichte wieder.
- Erfassungs- und Bearbeitungsformular mit Streamlit-AppTest gegen die echte getrennte PostgreSQL-Testdatenbank ausgeführt: Kennzahlen aktualisiert, Maßnahme geändert, Audit geprüft. Keine künstlichen Berichte im realen Nutzbestand gespeichert.
- Veraltete Bearbeitung abgewiesen. Historische Arbeitsfassung bearbeitbar, Originalinhalt unverändert. Datenbanktrigger verhindert Löschung und Änderung der Originalherkunft.
- Eingeschränkte Anwendungsrolle tatsächlich getestet: Bericht anlegen möglich; endgültiges Löschen und Umschreiben bestehender Auditzeilen abgewiesen.
- Eigene PostgreSQL-Instanz auf Port 55432 tatsächlich gestoppt und gestartet. Zuvor gespeicherter künstlicher Bericht in der isolierten Testdatenbank samt Audit blieb erhalten.
- Dump erzeugt und mit `pg_restore` in eine zweite separate Testdatenbank eingespielt. 46 Originalberichte plus neuer Testbericht und seine Historie erhalten. Testdatenbanken anschließend entfernt.
- Tatsächliche DuckDB-/pandas-Aggregate, Vorher/Nachher-Fenster, Filter, leere Auswahl, Originalexporte und Linienlücken weiterhin geprüft. Upload-Prüfungen schließen ungültige Formate, fehlende Zeitstempel, Überschreiben und identische Inhalte aus.
- Lokaler Datenabgleich nach der Umstellung erfolgreich: Excel, PostgreSQL-Originalwerte, historische DuckDB-Kopie und PostgreSQL-Dateiregister stimmen überein. Dies ist kein erneuter Vollscan aller 181 Millionen Werte; die früheren vollständigen Qualitätsberichte bleiben erhalten.
- SHA-256-Nachvergleich: **alle 143 zuvor erfassten Originaldateien unverändert**, einschließlich Excel, 106 Parquets und vorhandener Forschungsreferenzen. [Originalnachweis](originalpruefung_postgresql.txt).
- Installation aus der vereinfachten `requirements.txt` erfolgreich; `pip check`: keine beschädigten Abhängigkeiten.
- `start.cmd` mit PostgreSQL-Vorbereitung und Dashboard tatsächlich ausgeführt. HTTP-Start auf 127.0.0.1:8501 erfolgreich. VS-Code-F5-Konfiguration mit Vorbereitungstask geprüft; der neue F5-Ablauf wurde nicht zusätzlich durch einen nativen Tastendruck ausgeführt.
- Im echten Browser: vier Bereiche, Ausgangskennzahlen, Gerätesuche 806279, Servicehistorie, Erfassungsmaske und tatsächlicher Temperaturverlauf mit Lücke, warmen Werten und Gerätemeldungen kontrolliert. Schreibvorgänge wurden im isolierten AppTest geprüft, keine erfundenen Berichte im Nutzbestand angelegt.

## Fehler während der Entwicklung und Korrekturen

Browsernachweise des abschließenden Standes: [Geräte und vier Hauptbereiche](postgresql_geraete.png), [Erfassungsformular](postgresql_formular.png), [tatsächliche Kurve mit Linienlücke](postgresql_messkurve.png). Die Forschungsansicht zeigt das aktuelle Protokoll mit 45 bestandenen Tests und den erfolgreichen PostgreSQL-/Referenzabgleich.

Windows-Pipe-Vererbung beim Serverstart durch dateibasierte Prozessausgabe behoben. Zwei byteidentische veröffentlichte Ereignisdateien werden als getrennte ursprüngliche Herkunftszuordnungen erhalten; neue identische Uploads werden abgewiesen. Vorzeitiges SQLAlchemy-Autoflush bei noch unvollständigen Berichten und eine pandas-Leerauswahl, die Spalten entfernte, korrigiert. Die aufgeführten 45 bestandenen Tests stammen aus dem abschließenden Lauf nach diesen Korrekturen.

## Aufräumarbeiten

Sechs Haupttabs zu vier Bereichen zusammengeführt; doppelte operative Excel-Ladefunktion aus der App entfernt. Direkte Abhängigkeiten von den getesteten transitiven Versionsgrenzen getrennt (`requirements.txt`/`requirements-lock.txt`). README und Demo auf die aktuelle Architektur umgestellt, alte Fachanleitungen mit einem aktuellen Hinweis versehen. **Keine Forschungsdateien, notwendigen Prüfskripte, Historie, Originaldaten oder Sicherungen gelöscht.** Die bisherige DuckDB-Servicekopie bleibt ausdrücklich historische Referenz.

## Grenzen und offene Arbeit

Kein tatsächlicher Windows-Rechnerneustart durchgeführt; geprüft ist der Datenbank-Prozessneustart. Keine Last-, Mehrbenutzer- oder Internetsicherheitsabnahme. Keine Benutzeranmeldung, kein Rollenfrontend, keine PDF-Anhänge, keine automatische externe Sicherung. Bearbeiterangaben sind lokale Freitexte. Produktionsbetrieb über das lokale Konto hinaus erfordert zusätzliche Zugriffs- und Betriebskonzepte.

Wissenschaftlich offen bleiben unabhängige Serviceepisoden, vollständige Berichtprüfung, Geräteidentität und Uhrdrift, Mindestabdeckung, vergleichbare Betriebszustände, weitere Volltextliteratur und Abstimmung der Forschungsfrage. Keine Risikomodelle oder kausalen Reparaturwirkungen behauptet. [Fallprüfung 806279](fall_806279_pruefung.md), [Anforderungsübersicht](professor_anforderungen.md).
