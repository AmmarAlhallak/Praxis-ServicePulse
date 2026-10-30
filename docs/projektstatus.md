# Projektstatus ServicePulse

## PostgreSQL und vereinfachte Verwaltung am 30.10.2026

Vorheriger Stand durch Checkpoint `d170faa`, separaten Branch `development/postgresql-service-management`, Git-Bundle, DuckDB-/Excel-Kopie und Original-Prüfsummen gesichert. PostgreSQL 17 war bereits installiert; eigene lokale Instanz auf Port 55432 eingerichtet, bestehender Windows-Dienst unverändert. 46 historische Berichte mit Originalinhalt übernommen, 53 Geräte und 106 Messdateien registriert. Neue Berichte und versionierte Änderungen werden transaktional gespeichert; die vierteilige Oberfläche erhält den wissenschaftlichen Kern. [Testbericht](postgresql_testbericht.md), [Windows-Start](postgresql_windows.md), [Fallprüfung 806279](fall_806279_pruefung.md).

Die folgenden Abschnitte dokumentieren frühere Entwicklungsstände.


## Ergänzung: Forschungsfrage, Filter und geführte Fälle am 29.10.2026

Der zuvor nur lokale deutsche UI-Stand wurde **vor** dieser Weiterentwicklung in Commit `1c40d9a` gesichert. Es wurde keine ältere GitHub-Version übernommen. Forschungsfrage, Datenquellen, Methode, Zielgrößen, Kontrollen, berechnete Ergebnisse, Grenzen und offene Fragen sind jetzt im eigenen Dashboard-Bereich sichtbar.

Die Servicefilter starten mit allen Geräten und Kategorien sowie dem gesamten Zeitraum, ohne vorausgewählte Chiplisten. Zwei skalare Datumsfelder und eine explizite Zeitraumbegrenzung ersetzen den unvollständig gespeicherten Datumsbereich. Ungültige/unvollständige aktivierte Zeiträume wählen keine Einträge aus und erklären den Grund; ein alter Range-Zustand beeinflusst die neue Auswahl nicht. Aktive Filter werden stets angezeigt. Die Messfallanalyse hat eine eigene Auswahl mit optionaler Kopplung an die Servicefilter.

Drei belegte Fälle sind direkt auswählbar. Zusätzlich zu den unveränderten Mittelwerten werden Minima/Maxima und tatsächlich beobachtete Stunden vor, am und nach dem Servicetag abgefragt. 806279/28.06.2022: 2.869/1.440/10.075 Messpunkte; 49/24/168 Stunden mit mindestens einem gültigen Punkt. 806030/28.01.2015: 0/24/0 Punkte und keine berechenbaren Vorher-/Nachher-Mittelwerte. Der Quellenwiderspruch 806031/03.02.2023 bleibt ausdrücklich ungeklärt. Es werden keine Ausfallraten oder Reparaturwirkungen abgeleitet.

**35 automatisierte Tests bestanden** im vollständigen lokalen Bestand. Der schreibgeschützte Datenabgleich meldet weiterhin 46/24/11/5 und 106 Parquet-Dateien ohne Abweichung. Die vorhandenen Forschungsdaten wurden nicht erneut heruntergeladen. Für den laufenden Browser musste der Server nach einer Modulergänzung neu gestartet werden; reine Tests in frischen Prozessen ersetzen diesen Browsercheck nicht.

Nach dem Serverneustart im echten Browser geprüft: vollständige Standardfilter ohne Enddatumswarnung, Forschungsübersicht mit aktuellen Prüfnachweisen sowie alle drei direkt auswählbaren Fälle einschließlich Messlücke und Datumswarnung. Belege: [Fallanalyse](praxis_fallanalyse.png), [Messabdeckung und Einordnung](praxis_messabdeckung.png). Zusätzlich wurde eine Kopie der Projektquellen ohne lokale Daten und Datenbank getestet: 29 Tests bestanden, 6 datenabhängige Tests übersprungen (12,47 Sekunden). Das ersetzt nicht den vollständigen lokalen Lauf mit 35 bestandenen Tests (30,73 Sekunden).

Vorführung und fachlicher Stand: [praxis_demo_03_11.md](praxis_demo_03_11.md), [professor_anforderungen.md](professor_anforderungen.md). Die folgenden Abschnitte dokumentieren frühere Entwicklungsstände und deren damalige Testzahlen.

## Ergänzung: deutsche Benutzeroberfläche am 29.10.2026

Die vorhandene App wurde in fünf Bereiche gegliedert: Übersicht, Störungsanalyse, Temperatur & Betrieb, Datenqualität sowie Methodik & Quellen. Deutsche Kategorien, Messgrößen, Tabellenbezeichnungen, Datumsformate, Einheiten und Diagrammlegenden liegen in einer eigenen Darstellungsschicht. Originalwerte bleiben erhalten; der Serviceexport ergänzt deutsche Lesehilfen. Dateipfade, Rohmeldungen und vollständige Prüftabellen sind als Expertenansichten verfügbar. Der validierende Import wurde in ein separat testbares Modul ausgelagert und überschreibt keine vorhandenen Dateien.

Die überarbeitete Suite umfasst **29 bestandene Tests**, einschließlich Originalwert-Erhaltung, CSV, Import und Überschreibschutz, Lücken in Messkurven und kombinierter Filter. Der lokale Datenabgleich bestätigt unverändert 46/24/11/5 sowie 106 Parquet-Dateien. Die wissenschaftlichen Quelldaten wurden nicht erneut heruntergeladen. HTTP-Healthcheck und lokale Syntaxprüfung waren erfolgreich. Eine fehlerhafte Auswahl numerischer Ereignislisten als Messgröße wurde korrigiert; die skalaren SQL-Aggregate bleiben unverändert.

Bedienung, aktuelle Demo und technische Grenzen: [oberflaeche.md](oberflaeche.md). Die nachfolgenden Abschnitte dokumentieren frühere Entwicklungsstände mit damals 20 bzw. 16 Tests.

## Ergänzung: Windows-/VS-Code-Prüfung am 29.10.2026

Der bestehende Prototyp wurde erhalten und lokal für VS Code eingerichtet. Arbeitsbereich, `.vscode`-Konfigurationen, `start.cmd` und `scripts/check_local.py` sind ergänzt. Die Microsoft-Python-Erweiterungen wurden installiert. F5-Start im echten VS-Code-Fenster und CMD-Start aus einem anderen Arbeitsordner wurden ausgeführt und über HTTP geprüft. Der schreibgeschützte Abgleich bestätigt Excel, DuckDB und Parquet-Metadaten. Der abschließende Lauf umfasst **20 bestandene Tests**. Eine zuvor dabei gefundene Diagramm-ID-Kollision wurde behoben; freie Messzeitfenster und State-Behandlung wurden korrigiert.

Nachweise und genaue Grenzen: [windows_pruefung.md](windows_pruefung.md). Bedienung: [windows_vscode.md](windows_vscode.md). Architektur und echte SQL-Abfragen: [technik_sql.md](technik_sql.md). Kurzvorführung: [vscode_demo_03_11.md](vscode_demo_03_11.md). Der folgende Abschnitt dokumentiert weiterhin den ursprünglichen Implementierungsstand derselben Sitzung mit damals 16 Tests.

Stand: 29.10.2026. Dieses Protokoll beschreibt ausschließlich die in dieser Sitzung tatsächlich ausgeführten Arbeiten. Es behauptet keine früheren Programmierfortschritte. Ausgangszustand des Arbeitsordners: ausschließlich `fault_summary_R1.xlsx`, keine bestehende Dashboard-Implementierung.

## Ausgeführt und überprüft

- Anforderungen aus der beigefügten Textdatei gelesen; lokale Excel automatisch nach passendem Datenblatt erkannt und alle Originalfelder beibehalten.
- Vollständigen GitLab-Dateibaum, Commit, README, Setup, ETL-Code, Ressourcen, Metadaten-CSV und Fehlerdokumentationsstruktur geprüft. Code getrennt als Referenz aufbewahrt, nicht installiert/importiert.
- Artikelvolltext über Europe PMC beschafft und Methodik gelesen. Figshare-Metadaten und Datenlizenz gesichert. Keine explizite Codelizenz im Repository gefunden.
- Alle 106 veröffentlichten Parquets geladen, 6.013.873.936 Bytes. Alle lokalen Git-Blob-Prüfsummen stimmen mit dem GitLab-Dateibaum überein; zusätzlich SHA256 gespeichert.
- Vollständige Zeit-/RTD-Prüfung des veröffentlichten Messbestands durchgeführt; 181.309.902 Zeilen einschließlich Geräteereignissen. Ergebnisse je Datei in `data/processed/measurement_quality.csv`.
- Drei konfliktbehaftete Servicefälle als PDF gelesen, relevante Seiten gerendert und Datums-/Textkonflikte dokumentiert. Datumskonflikt 806031 visuell kontrolliert.
- Zwei vollständige Rohdatenstichproben mit selbst entwickelten Lesern geprüft. Revco RTD/Zeit für alle 14.552 Stichprobenzeilen reproduziert; Unit-Name-Konflikt protokolliert. Haier zeitbasierte Zuordnung für 88.582 Zeilen geprüft.
- Eigene Module, Streamlit-/Plotly-Dashboard, DuckDB-Tabellen/Views, Filter, Vorher/Nachher-Fenster, Geräteereignis-Offset, CSV-Exporte und validierender Parquet-Upload implementiert.
- 16 automatisierte Tests bestanden: reale Excel-Kennzahlen, Kontrollblatt, Filter, leere/fehlerhafte Eingaben, Quellenkonflikte, SQL-Abfragen, Zeitfenstergrenzen, Uhrenoffset, Rohdatenjoins, Import-Schema, App-Betrieb mit und ohne Messdateien sowie Gerätewechsel. Künstliche Daten ausschließlich in temporären Testfixtures.
- Streamlit lokal auf `127.0.0.1:8501` gestartet. HTTP-Healthcheck liefert `ok`. Übersicht und echte Messkurve im Browser kontrolliert; anfänglichen Hell-/Dunkel-Kontrastfehler behoben. Screenshot: `docs/dashboard_messkurve.png`.
- Git-Repository mit Branch main initialisiert. Noch kein Commit erstellt. Große Daten, Referenzquellen und virtuelle Umgebung sind in `.gitignore` ausgeschlossen.
- README, Datenanalyse, Quellen-/Lizenzdokumentation, Literatur, Forschungsfrage, Zeitplan, Importanleitung und Demo-Leitfaden erstellt.

## Verfügbare Resultate

46 Serviceeinträge an 24 Geräten; 11 Geräte mit mehreren Einträgen; 5 wiederholte Original-Gerät/Kategorie-Paare. 39 Servicetage mit Temperaturwerten, 29 Einträge mit mindestens einem Messpunkt in beiden angrenzenden Siebentagefenstern. Diese Zahlen belegen weder unabhängige Ausfälle noch lückenlose Messabdeckung. Die App zeigt die Unsicherheiten.

## Offen und ausdrücklich nicht als erledigt ausgewiesen

1. Vollständige manuelle Prüfung sämtlicher Serviceberichte und Festlegung unabhängiger Episoden.
2. Fachliche Entscheidung zum Excel-Datum 806031, Fehlertext 806030/808783 und Unit Name 806022 im Rohdatenordner 806018. Lokale Excel bleibt unverändert.
3. Vollständige unabhängige Neuverarbeitung aller Rohdaten. Der Dashboardbestand sind veröffentlichte Autorenparquets; eigene Rohdatenverarbeitung wurde an zwei Stichproben durchgeführt.
4. Validierung historischer Geräteuhren, Zeitzonen/Sommerzeit und möglicherweise zeitabhängiger Drift. Konstanten Autorenoffset allein als begrenzte Quellenkorrektur behandeln.
5. Mindestabdeckung und vergleichbare Betriebszustände für weitergehende Geräte-/Fenstervergleiche festlegen. Doppelte Messzeitstempel bewusst fachlich behandeln; aktuell bleiben sie erhalten.
6. Klärung einer expliziten Codelizenz vor Weiterverteilung von Autorenquellcode; Drittmaterial in Handbüchern/Serviceberichten separat einordnen.
7. Volltexte der zusätzlichen FDD-Literatur über Hochschulzugang lesen; derzeit wurden deren Metadaten und Abstracts geprüft.
8. Forschungsfrage und späteres Bachelorarbeitsszenario mit Prof. Blunck abstimmen. Keine Prognose, kein Training und keine behauptete Risikogüte implementiert.

## Zugriffsprobleme und Lösung

Git-Clone des sehr großen Repositorys wurde abgebrochen; öffentliche GitLab-API lieferte den vollständigen Baum und alle benötigten Dateien. Nature/DTU-Volltextzugriffe waren blockiert; Europe-PMC-XML war zugänglich. Das 9,8-GB-Figshare-ZIP wurde nicht geladen, da Einzelparquets verfügbar waren. Alle für die aktuelle App erforderlichen Daten sind lokal vorhanden. Exakte Wiederbeschaffung und Zielpfade stehen in `docs/datenimport.md`.
