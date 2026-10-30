# ServicePulse starten und bedienen

Stand 30.10.2026. Bestehender Arbeitsordner: `C:\Users\ammar\Downloads\fault_summary_R1`.

## Normaler Start

1. `start.cmd` doppelt anklicken oder in VS Code `ServicePulse.code-workspace` öffnen und F5 drücken.
2. Die Vorbereitung meldet „PostgreSQL bereit“. Browser unter http://127.0.0.1:8501 öffnen. Auf diesem Laptop sind die Forschungsdaten bereits importiert.
3. **Geräte & Serviceberichte** öffnen, Gerät suchen und auswählen.
4. Im Formular einen Bericht erfassen. Nur Gerät und Herkunft sind erforderlich. Unbekannte Herkunft ausdrücklich als „Nicht bekannt“ angeben; andere fehlende Felder bleiben gekennzeichnet.
5. **Servicebericht speichern** wählen. Bestätigung, Historie und Kennzahlen aktualisieren sich. Aktive Servicefilter können einen neuen Bericht aus der gefilterten Übersicht ausschließen; gegebenenfalls „Alle Filter zurücksetzen“ wählen.
6. Zum Bearbeiten „Bestehenden Bericht bearbeiten“ wählen und einen Änderungsgrund angeben. Bei einem Konflikt „Aktuellen Bericht neu laden“ verwenden. Erstquelle und historische Originalzeile bleiben erhalten.
7. Unter **Betriebsanalyse & Vergleiche** bei vorhandenen Messdaten eine Kurve öffnen. Ein neuer Bericht erzeugt keine Messpunkte.

Neue Geräte über **Neues Gerät anlegen** erfassen. Die ID muss eindeutig sein und sechs Ziffern enthalten. PDF-Anhänge und eine Löschfunktion sind nicht implementiert.

## PostgreSQL unter Windows

Die vorhandenen PostgreSQL-17-Programme betreiben eine eigene Instanz auf **127.0.0.1:55432**, gespeichert unter `data/postgresql`. Der vorher vorhandene PostgreSQL-Windows-Dienst bleibt unverändert. Docker ist hier nicht verfügbar und wird nicht benötigt. Es wurde kein zusätzlicher Datenbankserver installiert.

Nach einem Rechnerneustart startet die eigene Instanz beim nächsten F5-/`start.cmd`-Start erneut. Kein zusätzlicher Windows-Autostartdienst eingerichtet. Der Laptop selbst wurde während der Prüfung nicht neu gestartet; tatsächlich geprüft sind PostgreSQL-Prozessneustart und Wiederherstellung einer Sicherung in einer getrennten Testdatenbank.

`scripts/prepare_database.py` startet PostgreSQL, wendet Alembic-Migrationen an, prüft den einmaligen Excel-Import und neue Messdateien und erzeugt einen Dump. Ein erneuter Start importiert keine Duplikate. Auf einem anderen Rechner sind zunächst Python und offizielle PostgreSQL-Binärdateien zu installieren; anschließend `.venv` und `requirements.txt` verwenden. Ohne PostgreSQL erscheint ein Fehler, kein veralteter Excel-Ersatzbestand.

Geheimnisse liegen nur lokal in `data/private/postgres.json` und `.env`. Unter Windows sind diese für das aktuelle Konto freigegeben und aus Git ausgeschlossen. Nicht weitergeben. Die App nutzt eine eingeschränkte Datenbankrolle ohne Löschrecht und ohne Änderungsrecht an bestehenden Auditprotokollen. Es handelt sich um eine lokale Einzelplatzanwendung; Anmeldung und Rechteverwaltung für einen öffentlich erreichbaren Unternehmensserver fehlen noch.

## Sicherung

Vor der Umstellung: `data/backups/before_postgresql_20261030/` enthält die DuckDB mit Prüfberichten, Excel, ein Git-Bundle und SHA-256-Listen aller bisherigen Originaldaten. Parquets und Forschungsdateien blieben an ihrem bisherigen Ort. Git-Wiederherstellungspunkt vor der Umstellung: `d170faa`, vorheriger fertiger Prototyp: `4bef950`.

Jeder erfolgreiche Start erzeugt einen logischen PostgreSQL-Dump unter `data/backups/postgresql/`. Für eine Sicherung nach neuen Eingaben `scripts/prepare_database.py` erneut ausführen. Sicherungen zusätzlich auf einen eigenen externen Datenträger kopieren; dieselbe Festplatte schützt nicht vor deren Ausfall.

Wiederherstellung: Anwendung schließen, aktuellen Stand zusätzlich sichern und den gewählten Dump mit `pg_restore.exe` in eine **neue leere Datenbank** einspielen. Anschließend die lokale Verbindung bewusst umstellen. Nicht ungeprüft über den aktuellen Nutzbestand restaurieren. Der automatische lokale Starter bereitet weiterhin die eigene Datenbank `servicepulse` vor; abweichende externe Verbindungen erfordern eine bewusste Konfigurationsanpassung. Dump/Restore einschließlich neuem Bericht und Audit wird in getrennten Testdatenbanken geprüft.

Die frühere Version lässt sich über einen separaten Git-Worktree von `4bef950` öffnen, ohne den aktuellen Arbeitsordner zurückzusetzen. Die gesicherte DuckDB liegt im Sicherungsordner. Originaldateien dafür weder löschen noch ersetzen.

## Bei Startproblemen

- Port 8501 belegt: bestehendes Dashboard beenden, nur eine Instanz starten.
- PostgreSQL startet nicht: `data/postgresql.log` prüfen; keine Kennwörter weitergeben.
- Messdateien fehlen: [Datenimport](datenimport.md) verwenden. Serviceverwaltung bleibt mit PostgreSQL verfügbar.
- Nach Änderungen an Python-Modulen: Dashboard vollständig beenden und erneut starten, falls Streamlit noch alte Modulimporte verwendet.
