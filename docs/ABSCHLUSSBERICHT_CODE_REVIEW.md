# Abschlussbericht: ServicePulse-Code-Review

30.10.2026. Vorbereitung auf die Professor-Demo am 03.11.2026.

## Ergebnis und Wiederherstellbarkeit

Der lokale Prototyp ist für die dokumentierte Demonstration bereit. Windows-Start, echte Parquet-Analyse, Geräteverwaltung und getrennte PostgreSQL-Schreibtests funktionieren. Wissenschaftliche Einschränkungen bleiben sichtbar. Eine öffentliche Mehrbenutzeranwendung mit Anmeldung wird nicht behauptet.

Ausgangsbranch: `development/postgresql-service-management`, Commit `5b80a9d485ef61282cc46c37b027fe216bfcb4dd`. Arbeitsbranch: **`improvement/professor-demo`**. Der Ausgangsstand war sauber. `main` wurde nicht geändert oder gemergt; der bisherige Entwicklungsbranch bleibt als Rückweg erhalten. [Ausgangsprotokoll](review_ausgangsstand.md).

## Bestätigte Probleme und Behebung

| Tatsächlicher Befund | Änderung und Nachweis |
|---|---|
| Das Dateiregister wurde außerhalb der anfänglichen Datenbank-Fehlerbehandlung geladen. Verbindungsverlust konnte dort die Seite abbrechen. | Alle vier anfänglichen PostgreSQL-Abfragen sind gemeinsam geschützt. Auch Fehler beim Laden der Bearbeitungshistorie werden verständlich angezeigt. Regressionen für beide Ladefehler und den Historienfehler bestanden. |
| Eine leere Berichtstabelle lieferte nicht alle von der Oberfläche benötigten Spalten. | Stabile leere Spaltenstruktur, unter anderem Version, Status und Maßnahme. Test mit tatsächlich geleerten Tabellen ausschließlich in der Testdatenbank bestanden. |
| Maßnahmentext wurde vor der Speicherung getrimmt, im Audit-Kontext jedoch nicht. | Einheitlich getrimmter Text. Gleichzeitigkeitstest vergleicht gespeicherte Maßnahme und Auditwert. |
| Neue Parquets mit bestätigter Zeitzone konnten neben den historischen Zeitstempeln ohne bestätigte Zeitzone angenommen werden. | Gemeinsame Zeitspaltenprüfung für Import und Inventar. Keine stillschweigende Umrechnung; entsprechende Uploads benötigen eine explizite dokumentierte Zeitpolitik. |
| Jeder bisherige Start führte die komplette Vorbereitung einschließlich Importprüfung und Dump aus. | Normalstart prüft nur Server und Schemaversion. Migration, Synchronisation und Sicherung sind ausdrückliche Optionen. Ausstehende Migrationen werden gemeldet. Tatsächliche Starts ließen die Zahl vorhandener Dumps bei **7 → 7**. |
| Der CMD-/PowerShell-Start legte Port 8501 nicht ausdrücklich fest und konnte bei belegten Ports auf 8502/8503 ausweichen. | Beide Starter verwenden ausdrücklich 8501. Alte, eindeutig zum Projekt gehörende Dashboardprozesse wurden beendet. `start.cmd` startete anschließend tatsächlich auf 127.0.0.1:8501; HTTP-Gesundheitsprüfung und Browserprüfung erfolgreich. |
| Ein SQLite-Transaktionskontext im originalen Haier-Rohdatenleser schloss die Leseverbindung nicht. Zwei ResourceWarnings wurden im ersten Coverage-Lauf sichtbar. | `contextlib.closing` schließt die Verbindung ausdrücklich. Auch die synthetische Testdateiverbindung wird geschlossen. Regression prüft die tatsächlich geschlossene Verbindung; endgültiger Lauf ohne Warnungen. SQLite bleibt ausschließlich Rohdatenleser. |
| Die Gültigkeitsprüfung lokaler Testprotokolle kannte verschachtelte UI-Module noch nicht. | Alle Python-Module einschließlich UI, Skripten und Migrationen werden auf Aktualität geprüft. Neuer Regressionstest für `ui/operation.py`. |

Die Typangabe des SQLAlchemy-Servicedatums wurde von `datetime` auf das tatsächlich verwendete `date` korrigiert. Das ändert weder Datenbankschema noch Datenwerte.

## Verständlichere Struktur

`app.py` konfiguriert und lädt den Bestand und führt vier Bereiche zusammen. Übersicht, Betriebsanalyse und Qualitäts-/Forschungsansicht liegen unter `servicepulse/ui/`; die bestehende Geräteverwaltung bleibt in `management.py`. Gemeinsame Darstellung und Servicefilter haben eigene überschaubare Module. Bestehende Widgetkennungen, deutsche Beschriftungen, Farben, Diagramme und Berechnungen blieben erhalten.

Die öffentlichen Fachfunktionen besitzen sinnvolle Typangaben und kurze deutsche Zweckbeschreibungen. Ruff vereinheitlicht Importreihenfolge und Formatierung. Lange Ketten mehrerer Anweisungen pro Zeile wurden aufgelöst. Die größere sichtbare Zeilenzahl einiger Fachdateien kommt überwiegend von dieser lesbareren Formatierung, nicht von zusätzlichen Abstraktionsschichten.

`repository.py` bleibt eine bewusst direkte öffentliche API. Abschnitte trennen gemeinsame Prüfungen/Audit-Kontext, Forschungsimport, Messdateiregister sowie Geräte/Berichte/Historie. Eine Aufteilung in weitere Repositoryklassen wurde vor der Demo zurückgestellt: Der bestehende explizite Testverbindungsparameter und die zentrale Verbindungsersetzung sind bewährt; eine umfassende Verschiebung hätte zusätzliche Umstellungsrisiken ohne erforderlichen Funktionsgewinn.

Die Beispielknöpfe stimmen nun das Verwaltungsgerät mit dem untersuchten Beispiel ab. Umgekehrt bleibt der vorhandene Knopf „Dieses Gerät für die Betriebsanalyse auswählen“ erhalten. Servicefilter und Messzeitraum bleiben getrennt. Das Anlageformular ist weiterhin standardmäßig geschlossen; historische unbekannte Statuswerte und fehlende Maßnahmen erscheinen als „Nicht dokumentiert“.

## Datenbankprüfung

- SQLAlchemy-Sessions und Transaktionen werden über Kontextmanager geschlossen. Der Verbindungspool verwendet `pool_pre_ping`; die zusätzliche administrative Engine der Erstvorbereitung wird auch im Fehlerfall freigegeben.
- Bericht, Quelle, Maßnahme und Audit sind transaktional verbunden. Ein bewusst erst spät ausgelöster Constraintfehler hinterließ **keine** zusätzlichen Bericht-, Quellen-, Maßnahmen- oder Auditzeilen in der Testdatenbank.
- Zwei gleichzeitig gestartete Änderungen derselben Version ergaben genau **einen Erfolg und einen Konflikt**, Version 2 und genau zwei Auditversionen einschließlich Anlage.
- Alle drei Migrationen wurden auf leerer Testdatenbank angewendet. Der Vergleich von Alembic-Schema und SQLAlchemy-Modellen ergab keine Differenzen. Vorhandene Migrationen wurden nur formatiert; ihre Upgrade-/Downgrade-Operationen wurden zusätzlich per Python-AST auf unveränderten Inhalt geprüft.
- Eindeutige Import-/Anforderungsschlüssel, unveränderliche Forschungsoriginale und Quellenbezüge sowie Audit- und Löschschutz wurden geprüft. Wiederholter historischer Import fügte null Duplikate hinzu.
- SQL-Werte sind parametrisiert. Dynamische DuckDB-Spalten werden am Schema geprüft und maskiert; Intervalle sind fest begrenzt. Lokale Fehlermeldungen geben keine SQL-Parameter oder Kennwörter aus.
- Vorhandene Indizes auf Gerät, Servicedatum, Berichtshistorie, Pfad und Prüfsumme reichen für den kleinen Berichtbestand aus. Kein belegter Engpass erfordert einen weiteren Index oder eine neue Migration. Keine Schemaänderung am Nutzbestand vorgenommen.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis |
|---|---|
| Alle vorhandenen Tests **vor** den Änderungen | **47 bestanden**, 0 übersprungen, 0 Fehler; **72,86 s**. [Ausgabe](code_review_baseline.txt). |
| Endgültiger vollständiger Lauf auf diesem Windows-Laptop | **57 bestanden**, 0 übersprungen, 0 Fehler, **keine Warnungen**; **103,74 s**. [Ausgabe mit Abdeckung](code_review_testlauf.txt), lokales JUnit `docs/testlauf_review.xml`. |
| Abdeckung von `app.py` und `servicepulse/` | **92 %**: 1.330 ausführbare Anweisungen, davon 101 nicht ausgeführt. Start-/Downloadskripte und Migrationen gehören nicht zu diesem Coverage-Nenner; Migration und Backup/Restore werden trotzdem funktional geprüft. Keine feste Mindestgrenze erzwungen. |
| Bereinigte Kopie der versionierten/veröffentlichbaren Dateien, ohne `.env`, `data/` und `research/`; CI-Modus mit eigener PostgreSQL-Instanz | **50 bestanden**, **7 wegen tatsächlich fehlender optionaler Quelldateien übersprungen**, 0 Fehler, keine Warnungen; **65,99 s**, **78 %** Abdeckung. [Ausgabe einschließlich aller Skipgründe](code_review_ci.txt). Das ist ein lokal ausgeführter CI-Vergleich, kein behaupteter GitHub-Runner-Lauf. |
| `ruff check .` / `ruff format --check .` | Erfolgreich; 42 Python-Dateien einheitlich formatiert. |
| `pip check` und Installation aus `requirements-dev.txt` | Erfolgreich, keine widersprüchlichen Paketanforderungen. |
| `scripts/check_local.py` | Excel, erhaltene PostgreSQL-Originale, historische DuckDB-Prüfreferenz und Messdateiregister stimmen überein. Kennzahlen **46 / 24 / 11 / 5**, **53 Geräte**, **106 Dateien**, **181.309.902 Zeilen**. |
| Echtes `start.cmd` nach dem Aufräumen alter Dashboardprozesse | Server bereit, keine Migration/Import/Sicherung; Streamlit unter **8501**, HTTP `/_stcore/health` = `ok`. VS-Code-Konfiguration und Vorbereitungsschritt geprüft; F5 wurde bei diesem Review nicht zusätzlich als Tastendruck ausgeführt. |
| Echter Browser | Übersicht und Kennzahlen, Geräteverwaltung, Öffnen/Schließen des Anlageformulars ohne Speicherung, Fall 806279 mit sichtbarer Lücke geprüft. [Screenshot](review_betriebsanalyse.png). |
| Originalschutz | Alle acht Nutzdatenbanktabellen haben identische vollständige Inhaltsprüfsummen gegenüber dem Reviewbeginn. **142 Forschungsdateien + 1 Excel** vollständig per SHA-256 unverändert. [Prüfprotokoll](originalpruefung_review.txt). |

Die sieben optionalen Prüfungen betreffen reale Gerätemessdateien, den Autoren-CSV-Vergleich, die vorhandene historische DuckDB-Prüfreferenz und reale Forschungsfälle. Sie sind als `local_data` gekennzeichnet. Auf diesem Laptop wurden **alle sieben ausgeführt und bestanden**. Kein Test wurde entfernt oder zum Erzwingen eines grünen Ergebnisses pauschal deaktiviert.

Die Tests decken Geräteanlage, Berichtsanlage, Speicherung per SQL-Abfrage, Wiederanlauf nach tatsächlichen Dashboard-Prozessstarts, Bearbeitung, Audit, Statistik, doppelte Importe, Herkunftstrennung, parallele Änderungen, Rollback, Rollenrechte, PostgreSQL-Neustart und Dump/Restore ab. Schreibversuche erfolgen ausschließlich in kurzlebigen Testdatenbanken auf einer eigenen Instanz mit zufälligem Port und erzeugten Zugangsdaten. Die Nutzinstanz auf 55432 wird dafür nicht gestoppt oder beschrieben.

## GitHub Actions

`.github/workflows/checks.yml` installiert die festgehaltenen Python-Abhängigkeiten, prüft Ruff und führt pytest mit Coverage aus. `tests/conftest.py` erzeugt eine eigene native PostgreSQL-Instanz mit zufälligen Zugangsdaten. Im CI-Modus erhalten gewöhnliche Oberflächentests eine zusätzliche getrennte Excel-Demodatenbank; Schreibtests verwenden weiterhin ihre eigene Datenbank. Die sechs Gigabyte Parquets und lokale Geheimnisse werden nicht vorausgesetzt. Die [offizielle Windows-Runner-Dokumentation](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md#postgresql) beschreibt die vorhandenen PostgreSQL-Programme; alternativ kann deren Ordner über `SERVICEPULSE_PG_BIN` angegeben werden.

Der tatsächliche GitHub-Lauf nach Veröffentlichung ist separat vom oben belegten lokalen Testlauf zu beurteilen. Ruff-Konfiguration und Coverage-Berichte folgen der [Ruff-Dokumentation](https://docs.astral.sh/ruff/configuration/) und [pytest-cov-Dokumentation](https://pytest-cov.readthedocs.io/en/latest/reporting.html).

## Wissenschaftlich unverändert und bewusst offen

Fall **806279, 28.06.2022** bleibt mit 2.869 / 1.440 / 10.075 gültigen RTD-Punkten in Vorher-/Tag-/Nachher-Fenstern reproduziert. Vorher sind 49 von 168 Stunden beobachtet, nachher 168. Mittelwerte −64,01 / −79,90 °C; maximale Temperatur vorher +21,8 °C; mehrtägige Lücke sichtbar. Unabhängige pandas-Aggregation stimmt mit DuckDB überein. Keine Interpolation, keine Ausreißerentfernung und keine behauptete Reparaturkausalität.

Bewusst nicht umgesetzt: größere Repositoryarchitektur, zusätzliche Datenbanktechnologie, Übertragung aller Sensordaten nach PostgreSQL, unbelegte neue Indizes, riskante Nutzdatenmigrationen, automatische Korrektur von Quellenkonflikten, frei erfundene Maßnahmen, Prognosemodell oder behauptete Ausfallwahrscheinlichkeiten. Keine Anmeldung, öffentliche Mehrbenutzerbereitstellung oder vollständige unabhängige Rohdatenrekonstruktion. Die bekannte Kennungsabweichung 806018/806022, drei Quellenkonflikte, die unbestätigte Zeitzone und die Abgrenzung unabhängiger Störungsepisoden bleiben fachliche Aufgaben. Der Windows-Laptop selbst wurde während dieses Reviews nicht neu gebootet.

## Betroffene Dateien und nachvollziehbare Commits

Die Commits trennen Ausgangsnachweis, bestätigte Fehler, Formatierung vorhandener Skripte/Migrationen, typisierte Fachfunktionen, UI-Aufteilung, Start/CI sowie diese Dokumentation. Der vollständige Dateivergleich ist über `git diff --stat 5b80a9d..HEAD` und die einzelnen Commits nachvollziehbar.

Wesentliche Änderungen: `app.py`, `servicepulse/ui/`, alle vorhandenen Fachmodule mit Typen/Docstrings und Formatierung, `scripts/prepare_database.py`, `start.cmd`, `start.ps1`, `.vscode/{launch,tasks}.json`, `tests/conftest.py`, ergänzte/formatierte Tests, `pytest.ini`, `pyproject.toml`, `requirements-dev.txt`, `requirements-lock.txt`, `.github/workflows/checks.yml` und aktualisierte Start-/Architekturdokumentation. Die vorhandenen übrigen Wartungsskripte und Migrationen erhielten Formatierung. Neue Anleitungen: [Projekt erklären](PROJEKT_ERKLAERUNG.md) und dieser Bericht.
