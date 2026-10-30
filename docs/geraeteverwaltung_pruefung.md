# Geräteverwaltung und PostgreSQL: erneute Prüfung am 30.10.2026

**Neuer Stand nach Code-Review:** 57 Tests bestanden, keine übersprungenen Tests und keine Warnungen. Siehe [aktuellen Abschlussbericht](ABSCHLUSSBERICHT_CODE_REVIEW.md). Die folgenden Zahlen dokumentieren den früheren Stand vor diesem Review.

## Ergebnis

Vollständige Testsuite: **47 bestanden, 0 fehlgeschlagen, 0 übersprungen**, Laufzeit **75,25 Sekunden**. Tatsächliche Ausgabe: [testlauf_postgresql.txt](testlauf_postgresql.txt). JUnit-Protokoll lokal: `docs/testlauf_postgresql.xml`.

Schreibtests laufen jetzt nicht nur in einer getrennten Datenbank, sondern in einer **eigenen temporären PostgreSQL-Instanz** mit freiem lokalen Port, eigenem Datenverzeichnis und eigenen Zugangsdaten. Auch der PostgreSQL-Neustarttest betrifft ausschließlich diese Testinstanz. Die Testdatenbanken und die Testinstanz werden anschließend beendet bzw. entfernt. Der Forschungsserver auf Port 55432 wird von den Tests nicht neu gestartet.

## Die acht angefragten Schritte

| Schritt | Tatsächlich ausgeführte Prüfung | Ergebnis |
|---|---|---|
| 1. Gerät anlegen | Über das echte Streamlit-Formular im AppTest Gerät `999992` angelegt; PostgreSQL-Geräteliste gelesen | Gerät vorhanden, keine erfundenen Messdaten |
| 2. Servicebericht erfassen | Neues Formular geöffnet, Beschreibung und Quelle eingegeben, Speichern ausgelöst | Ein zusätzlicher Testbericht gespeichert |
| 3. PostgreSQL-Nachweis | Direkte SQL-Abfrage auf `service_reports` nach Geräte-ID | Bericht mit `origin='manual'`, ohne historische Originalzeile vorhanden |
| 4. Dashboard neu starten | Zwei echte Streamlit-Serverprozesse nacheinander auf separatem freien Port gestartet, jeweils HTTP-Healthcheck erfolgreich, anschließend frischen Dashboardzustand mit AppTest geladen | 47 Berichte und neuer Geräteeintrag bleiben erhalten; künstlicher Bericht sichtbar |
| 5. Bericht bearbeiten | Im Formular Maßnahme ergänzt, Status auf abgeschlossen geändert und Änderungsgrund eingetragen | Version 2 mit korrektem Vorher/Nachher, Maßnahme und Grund protokolliert |
| 6. Statistik prüfen | Dashboard-Kennzahlen vor/nach Speichern und nach Bearbeitung verglichen | Einträge 46 → 47, betroffene Geräte 24 → 25; Mehrfacheinträge 11 und wiederholte Paare 5 bleiben korrekt |
| 7. Historischen Import wiederholen | Nach Anlage des eigenen Berichts zweimal `import_research` ausgeführt | Jeweils null neue Zeilen; Gesamtzahl bleibt 47 |
| 8. Herkunft trennen | SQL-Herkunft, fehlende historische Zeilenzuordnung beim neuen Bericht und vollständige ursprüngliche DataFrames verglichen | Weiterhin exakt 46 unveränderte Forschungsoriginale und ein separat gekennzeichneter eigener Testbericht |

Das Testdatenbank-Beispiel importiert die 24 Geräte aus den Servicezeilen und ergänzt ein Testgerät. Es ist keine Kopie der 53 registrierten Geräte des Nutzbestands. Die PostgreSQL-Schreibprüfungen und AppTests sind automatisiert; es wurde kein künstlicher Bericht über den Browser in den Nutzbestand geschrieben.

Weitere bestehende Prüfungen bestanden ebenfalls: PostgreSQL-Neustart mit erhaltenem Bericht/Audit, eingeschränkte Anwendungsrolle, veraltete Bearbeitung, Original-/Löschschutz, Dump/Restore, Importe, DuckDB-/pandas-Abgleich, Filter, Zeitfenster und Messlücken.

## Bedienung und fehlende historische Angaben

Die Erfassungsmaske ist standardmäßig verborgen. Der hervorgehobene Knopf **Neuen Servicebericht erfassen** öffnet sie, **Formular schließen** verbirgt sie wieder. Nach erfolgreichem Speichern wird sie ebenfalls geschlossen. Die Bearbeitung vorhandener Berichte bleibt separat auswählbar.

Fehlende historische Maßnahmen sowie der intern unbekannte Status `nicht angegeben` werden in den lesbaren Tabellen als **Nicht dokumentiert** angezeigt. Im Bearbeitungsformular trägt die leere historische Maßnahme denselben Platzhalter und die unbekannte Statusoption dieselbe Beschriftung. Das sind reine Anzeigeänderungen: kein erfundener Maßnahmeninhalt, kein automatisch angenommener Abschluss und keine Umschreibung der Datenbankwerte. Ein automatisierter Vergleich bestätigt unveränderte Berichtsdaten nach bloßem Anzeigen und Öffnen/Schließen der Maske.

## Schutz des Nutzbestands

Im laufenden Browser zusätzlich geprüft: Formular über den Knopf geöffnet und wieder geschlossen, historische Status- und Maßnahmenfelder als „Nicht dokumentiert“ angezeigt. Dabei nichts gespeichert. [Screenshot des überprüften Endzustands](geraeteverwaltung_geprueft.png).

Vorher/Nachher wurden alle Datensätze der acht produktiven Tabellen schreibgeschützt gelesen, stabil sortiert und per SHA-256 verglichen. **Alle acht Tabellen sind inhaltlich unverändert:** 53 Geräte, 46 Berichte, 106 Messdateien, 46 Auditzeilen und keine neu angelegten Maßnahmen. Auch Kategorien, Quellen und Schema-Versionszeile stimmen überein. Die lokalen Vergleichsdateien liegen unter `data/private/management_before.json` und `management_after.json` und sind aus Git ausgeschlossen.

Zusätzlich stimmen **alle 143 zuvor erfassten Originaldateien** mit ihren gesicherten SHA-256-Werten überein, einschließlich Original-Excel, 106 Parquets und vorhandener Forschungsreferenzen. Der lokale Excel-/PostgreSQL-/DuckDB-/Dateiregister-Abgleich war ebenfalls erfolgreich.

Der laufende produktive Dashboard-Prozess wurde zur Aktivierung der neuen Oberfläche neu gestartet; der produktive PostgreSQL-Server blieb dabei aktiv. Die automatisierten Tests selbst verwenden für Neustarts nur ihre temporäre Instanz bzw. separate Dashboard-Prozesse. Kein erneuter kompletter Windows-Neustart und kein Last- oder Mehrbenutzertest behauptet.

## Reproduktion

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/testlauf_postgresql.xml
.\.venv\Scripts\python.exe scripts/check_local.py
```

Die temporäre PostgreSQL-Instanz benötigt die bereits vorhandenen PostgreSQL-Binärdateien. Die Originalmessdateien werden von den betreffenden Prüfungen nur gelesen.
