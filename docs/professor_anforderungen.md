# Anforderungen der Praxisphase: nachvollziehbarer Stand

Stand 29.10.2026. „Erfüllt“ bezieht sich auf den vorhandenen Prototyp und nachgewiesene Arbeit, nicht auf eine bereits erfolgte akademische Abnahme.

| Anforderung | Stand | Vorhandener Nachweis | Noch erforderlich |
|---|---|---|---|
| 1. Konkrete, beantwortbare Forschungsfrage | Teilweise erfüllt | vorläufige Frage in `forschungsfrage.md` und eigenem Dashboard-Bereich; Gegenstand und Grenzen sind abgegrenzt | endgültige Formulierung und Umfang mit Prof. Blunck abstimmen |
| 2. Messbare Zielgrößen und Vergleichsmaßstäbe | Erfüllt für den deskriptiven Prototyp | Einträge/Geräte/Kategorien, Wiederholungen, Zeitfensterstatistik, Messpunkt- und Stundenabdeckung; Excel-Kontrollblatt, SQL-/pandas-Prüfung | Mindestabdeckung und vergleichbare Betriebsbedingungen für weitergehende Vergleiche festlegen |
| 3. Echte Datenaufbereitung und beschreibende Statistik | Erfüllt für den vorhandenen Datenbestand | eigene Excel-Aufbereitung, direkte Parquet-Abfragen, Qualitätsprüfungen, 46 Einträge, 106 Parquets; zwei eigene Rohdatenstichproben | vollständige unabhängige Rohdatenrekonstruktion ist nicht erledigt und nicht als solche ausgewiesen |
| 4. Interaktives Analyse-Dashboard | Erfüllt als lokaler Prototyp | deutsche Oberfläche, Servicefilter, sechs Schritte der Fallanalyse, reale auswählbare Fälle, Export und geschützter Import | Benutzerrückmeldungen und Betreuerfeedback aufnehmen |
| 5. Datenqualität, Herkunft und Nutzung | Teilweise erfüllt | dokumentierte CC0-Daten- und CC-BY-Artikellizenz, Herkunft/Commit, Prüfberichte, Quellenkonflikte und Gerätekennungsproblem offengelegt | individuelle Drittunterlagen/Codelizenz klären, alle Serviceberichte und Gerätezuordnungen fachlich prüfen |
| 6. Kritische Einordnung weniger Störungen | Erfüllt in Darstellung und Methodik | Serviceeinträge werden von unabhängigen Ausfällen getrennt; keine Ausfallraten, Kausalwirkungen oder Prognosegüten behauptet | eine unabhängige Ereigniszahl bleibt ohne Episodenprüfung unbekannt |
| 7. Zeitplan und wissenschaftliche Literatur | Teilweise erfüllt | Restzeitplan bis Anfang Dezember, überprüfbare FDD-/Leckagequellen mit DOI und Relevanz | systematische Volltextauswertung der weiteren Fachliteratur und tatsächliche Umsetzung des Plans; geplante Wochen nicht als erledigt verbuchen |
| 8. Vorbereitung späterer Referenzverfahren | Teilweise erfüllt | transparente deskriptive Kontrollen und dokumentierte Perspektive für einfache Baselines | Zielereignis, Vorhersagehorizont, Exposition und Validierungsdesign zuerst klären; keine Modelle trainiert oder validiert |

## Was bereits geprüft wurde

- Kategorienhäufigkeiten aus Einzelzeilen gegen die zehn zusammengefassten Gruppen des zweiten Excel-Blatts.
- Übereinstimmung der Excel-Inhalte, DuckDB-Tabellen/Views und aktuellen Parquet-Metadaten.
- Stundenaggregate einer tatsächlich vorhandenen Messdatei zusätzlich gegen unabhängig mit pandas berechnete Werte.
- Messpunktabdeckung der 46 Servicetage und ihrer angrenzenden Siebentagefenster.
- Drei gezielte Serviceberichtfälle und zwei vollständige Rohdatenstichproben, wie in `repository_pruefung.md` dokumentiert; keine behauptete vollständige Berichtprüfung.

Für den aktuellen Softwarestand sind der ausgeführte pytest-Lauf und der lokale Abgleich maßgeblich. Das Dashboard kennzeichnet fehlende oder veraltete Protokolle statt automatisch einen Erfolg zu behaupten. Dokumentierte numerische Fallbeispiele werden live erneut aus den Parquets abgefragt.

## Offene fachliche Entscheidungen

Unabhängige Serviceepisoden, Fehlerbeginn gegenüber Auftrags-/Reparaturdatum, Geräteidentität 806018/806022, historische Uhren, ausreichende Messabdeckung und vergleichbare Betriebszustände. Erst danach ist zu entscheiden, ob eine spätere Risiko- oder Prognosefrage mit dieser kleinen Ereignisbasis belastbar untersucht werden kann.
