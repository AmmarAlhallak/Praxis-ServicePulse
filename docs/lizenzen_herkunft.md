# Lizenzen und Herkunft

Prüfdatum: 29.10.2026. Keine Rechtsberatung; hier werden verifizierte Kennzeichnungen dokumentiert, keine pauschalen Rechte für alle Repositorydateien abgeleitet.

| Bestandteil | Quelle und verifizierter Stand | Behandlung in ServicePulse |
|---|---|---|
| Veröffentlichung | Huang et al. (2023), Scientific Data 10:888, DOI 10.1038/s41597-023-02808-6; CC BY 4.0 im Artikel | Zitiert, Methodik kritisch eingeordnet |
| Figshare-Datensatz | API `https://api.figshare.com/v2/articles/24033324`: Lizenzname CC0, Link https://creativecommons.org/publicdomain/zero/1.0/ | Datenherkunft dokumentiert; Metadaten in `research/figshare_metadata.json` gesichert |
| GitLab-Quellcode | Commit `2779f6043fd9d3a7e1b8b1fe0c0f857735684b69`; keine LICENSE/COPYING/Copyright-Datei im vollständigen Dateibaum gefunden, setup.py ohne license-Angabe | Nur separate Referenzkopie, keine Übernahme von Code in eigene Module; öffentlich lesbar bedeutet nicht automatisch frei lizenzierter Code |
| GitLab-Parquets | `data/dataset/{Revco,Haier}/*_{temp,events}.parquet`; unverändert heruntergeladen | wissenschaftliche Daten, als Autorenverarbeitung gekennzeichnet; Einzeldateien stammen vom GitLab-Spiegel, keine Byteidentität zum Figshare-ZIP geprüft |
| Lokale Excel | `fault_summary_R1.xlsx`, erstes Blatt gleich dem Repository-Exemplar | Primäre Quelle für Serviceauswertungen; keine automatische Konfliktkorrektur |
| Serviceberichte und technische Handbücher | Drittmaterial im Repository; Figshare-Lizenzkennzeichnung beweist nicht gesonderte Rechteklärung jeder Drittunterlage | Gezielte lokale Prüfung, keine Einbettung von Namen, Telefonnummern oder Unterschriften im Dashboard, keine eigene pauschale Lizenzierung |
| Eigene Arbeit | `app.py`, `servicepulse/`, `scripts/`, `tests/`, Projekt-Dokumentation | neu entwickelte Verarbeitung, Prüfregeln und Benutzeroberfläche; keine erfundenen Messwerte |

CC0 der Daten und CC BY 4.0 des Artikels sind getrennt zu behandeln. Artikelverwendungen erfordern die Bedingungen von CC BY einschließlich Attribution und Kennzeichnung von Änderungen. Die Quellen werden auch bei CC0 aus wissenschaftlicher Redlichkeit genannt. Eine Nutzung oder Weiterverteilung des Autorencodes sollte vorab durch explizite Codelizenz oder Auskunft der Rechteinhaber geklärt werden. ServicePulse importiert oder startet diesen Code nicht.

Downloadmanifest: `research/download_manifest.json` mit Quellpfad, Abruf-URL, Commit, Bytezahl, lokalem SHA256 und Git-Blob-SHA1. Alle 106 Parquets wurden zusätzlich gegen die vom GitLab-Dateibaum angegebenen Blob-IDs geprüft und stimmen überein (`git_blob_verified: true`). Dies belegt Byteidentität zum geprüften GitLab-Stand, keine fachliche Richtigkeit der Daten. Excel-SHA256: `99d77c40d8ab6f98e09ae99c5d362f16db4558228ae267968c69c480b305e925`.

Der Artikelvolltext war direkt bei Nature/DTU durch Weiterleitung bzw. HTTP 403 blockiert. Er wurde über den Europe-PMC-Volltextdienst für `PMC10710515` abgerufen und als XML/Text lokal unter `research/article.*` gespeichert: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10710515/fullTextXML . Die Figshare-API und die GitLab-API waren zugänglich.
