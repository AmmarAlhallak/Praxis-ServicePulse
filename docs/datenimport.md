# Datenimport und Wiederbeschaffung

Am 29.10.2026 wurden alle 106 veröffentlichten Parquets erfolgreich geladen; aktuell musst du für das Dashboard keine weiteren Messdateien herunterladen. Gesamter Rohdatenbestand und das Figshare-ZIP sind nicht erforderlich. Die App funktioniert bei fehlenden Parquets weiterhin mit Excel.

## Automatischer selektiver Download

Aus dem Projektverzeichnis:

```powershell
.\.venv\Scripts\python.exe scripts/inspect_repository.py
.\.venv\Scripts\python.exe scripts/download_data.py
.\.venv\Scripts\python.exe scripts/build.py
```

Referenzmetadaten stehen in `research/gitlab_tree.json`, `gitlab_commit.json`, `figshare_metadata.json`; Downloads in `download_manifest.json`. `inspect_repository.py` erfasst alle Seiten des Dateibaums, speichert Code und kleine Text-/Tabellenquellen als Referenz. Der Download liest einen festgehaltenen Commit. Bestehende Dateiinhalte werden vor Wiederverwendung anhand des Git-Blob-Hash geprüft, fehlerhafte Teilstände erneut angefordert. Bei Fehlern Manifest prüfen und Befehl erneut ausführen. Erfolgreiche Dateien bleiben erhalten.

## Manueller Weg über GitLab

Quelle: https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data/-/tree/main/data/dataset . Für jedes gewünschte Gerät beide Dateien herunterladen:

| Repositorydatei | Projektziel unter `C:\Users\ammar\Downloads\fault_summary_R1` |
|---|---|
| `data/dataset/Revco/806279_temp.parquet` | `data\raw\Revco\806279_temp.parquet` |
| `data/dataset/Revco/806279_events.parquet` | `data\raw\Revco\806279_events.parquet` |
| `data/dataset/Haier/809169_temp.parquet` | `data\raw\Haier\809169_temp.parquet` |
| `data/dataset/Haier/809169_events.parquet` | `data\raw\Haier\809169_events.parquet` |
| `data/raw_data/other_data/time_offsets.csv` | `research\reference\data\raw_data\other_data\time_offsets.csv` |
| `data/raw_data/other_data/freezer_faults.csv` | `research\reference\data\raw_data\other_data\freezer_faults.csv` |
| `data/dataset/fault_summary_R1.xlsx` | bei Wiederbeschaffung zunächst `research\reference\data\dataset\fault_summary_R1.xlsx`; vorhandene lokale Excel nicht ungeprüft überschreiben |

Diese Muster gelten für alle weiteren sechsstelligen IDs. Vollständige Liste in `research/gitlab_tree.json`. Download-Schaltfläche „Raw“ verwenden, keine HTML-Webansicht als `.parquet` speichern. Die Datei muss von pyarrow lesbar sein. Eine Git-LFS-Zeigerdatei ist keine Messdatei.

## Figshare als Alternative

https://doi.org/10.6084/m9.figshare.c.6805332.v1 → Artikel 24033324 → Datei **ult-freezer-data-ssi-main.zip**, Datei-ID **43219173**.

Direktdownload: https://ndownloader.figshare.com/files/43219173 . Verifizierte Metadaten: **9.802.967.249 Bytes**, MD5 **de9a081b3acb2d01320c27ebb74c900c**. Für manuellen Download `data\external\ult-freezer-data-ssi-main.zip` anlegen; dort entpacken. Anschließend die enthaltenen `data/dataset/Revco`- und `Haier`-Parquets in die oben genannten `data/raw`-Ziele kopieren. Archivinhalt wurde hier nicht heruntergeladen; exakten äußeren ZIP-Wurzelordner beim Entpacken prüfen. MD5 mit `Get-FileHash -Algorithm MD5` vergleichen. Die ZIP-Datei ist zusätzlich zum Entpackungsplatz fast 9,8 GB groß.

## Rohdatenprüfung erweitern

`scripts/fetch_samples.py` lädt drei ausgewählte Serviceberichte, die Revco-Oktoberdatei für 806018 und die SQLite-Datei von Haier 809169 in `research/samples/` mit originaler Ordnerstruktur. `scripts/audit_samples.py` prüft diese Stichproben und Messabdeckung der 46 Excel-Zeilen. Für eine vollständige Rohdatenrekonstruktion wären insbesondere alle weiteren Revco-`.dat` und Haier-`.db` sowie fachliche Entscheidungen zu Geräteidentität, Zeitkorrektur und Duplikaten nötig. Diese Rekonstruktion ist derzeit nicht als fertig ausgewiesen.

## Import im Dashboard

Unter „Zeitliche Verläufe“ → „Weitere Parquet-Datei importieren“. Dateiname muss `<sechsstellige_ID>_temp.parquet` oder `<sechsstellige_ID>_events.parquet` sein. Importziel `data/raw/imported/`; vorhandene Zieldateien werden nicht überschrieben. Pflichtfeld `Datetime` muss ein Arrow-Zeitstempel sein. Temperaturdateien brauchen mindestens eine numerische Messgröße. Erwartete Zeitkonvention: `_temp` bereits korrigiert, `_events` interne Geräteuhr wie in der Autorenpipeline; andere Konventionen vorher klären. Eigenes Fremdmaterial benötigt separat dokumentierte Herkunft/Lizenz. Bei mehreren Dateien derselben Geräte-ID ist die konkrete Messdatei zu wählen; eine Geräteereignisdatei wird nur bei eindeutiger Zuordnung verknüpft. Nach Dateikopien App neu ausführen und den Build für persistierte Qualitätsberichte erneut starten.
