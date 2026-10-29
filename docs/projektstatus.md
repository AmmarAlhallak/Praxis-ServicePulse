# Projektstatus ServicePulse

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
