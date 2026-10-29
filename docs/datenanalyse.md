# Tatsächliche Datenanalyse

Stand 29.10.2026. Alle Zahlen in diesem Dokument stammen aus der lokalen Excel und den unverändert heruntergeladenen Parquets, soweit nicht ausdrücklich als Publikationsangabe bezeichnet. Reproduktion: `scripts/build.py` und `scripts/audit_samples.py`.

## Servicequelle

Datei `fault_summary_R1.xlsx`, Datenblatt `freezer_faults_info`, 46 Zeilen und 4 ursprüngliche Spalten: `freezer_id`, `registered_date`, `main_fault`, `Fault categories`. Zweites Blatt `Fault categories`: 10 zusammengefasste Gruppen mit Häufigkeiten. Das Datenblatt ist inhaltlich identisch mit dem separat geladenen Repository-Datenblatt.

| Kennzahl | Ergebnis |
|---|---:|
| Serviceeinträge | 46 |
| Unterschiedliche betroffene Geräte | 24 |
| Geräte mit mehr als einem Eintrag | 11 |
| Gerät/Kategorie-Paare mit mehr als einem Eintrag, Originalkategorien | 5 |
| Ungültige Datumswerte | 0 |
| Ungültige sechsstellige Gerätekennungen | 0 |
| Identische doppelte Originalzeilen | 0 |
| Einträge der Kategorie Data missing | 4 |
| Einträge mit No fix in Kategorie | 8 |

Registrierungszeitraum: 29.07.2014 bis 12.04.2023. Sämtliche Registrierungsdaten besitzen Tagesauflösung; 00:00 bei normalisierten Datumswerten ist keine gemessene Uhrzeit. Die vier Originalspalten haben keine fehlenden Werte. Die Leerraumprüfung der Kategorien ergibt 0 betroffene Zeilen; `category_raw` erhält dennoch den ursprünglichen Text, `category` entfernt bei späteren Importen nur äußere Leerzeichen.

| Originalkategorie, Leerraum bereinigt | Einträge |
|---|---:|
| Refrigerant leakage | 11 |
| 2nd stage compressor | 7 |
| Electrical malfunction | 7 |
| Unstable operation (No fix) | 5 |
| Data missing | 4 |
| 1st stage compressor | 4 |
| High condensation (No fix) | 2 |
| Bad insulation | 2 |
| Door tightness | 2 |
| Wrong setpoint | 1 |
| 1st stage compressor (No fix) | 1 |

Die zusammengefasste Kategorie „1st stage compressor“ enthält 5 Einträge, wenn No fix einbezogen wird. Die 10 Gruppen des zweiten Blatts ergeben dieselben zusammengefassten Häufigkeiten. „Data missing“ wird nicht als fehlende Excel-Zelle interpretiert und nicht einer Fehlerursache zugeschlagen. Die Zahl 11 bezieht sich auf als Leckage kategorisierte Einträge; zusätzliche Leckagetexte stehen unter Data missing. Kategorien und Fehlertexte sind deshalb verschiedene Auswertungsebenen.

## Messdatenbestand und Prüfung

106 Dateien, 53 Geräte: 38 Revco und 15 Haier. Es liegen jeweils Temperatur- und separate Geräteereignisdateien vor. Größe 6.013.873.936 Bytes. 181.309.902 Zeilen insgesamt:

| Modell | Temperaturzeilen | Geräteereigniszeilen |
|---|---:|---:|
| Revco | 179.594.746 | 144.573 |
| Haier | 1.551.875 | 18.708 |

Alle 106 Dateien wurden geöffnet und vollständig auf Zeitstempelanzahl, Zeitgrenzen, fehlende Zeitwerte, wiederholte Zeitstempel und zeitliche Lücken geprüft. Temperaturdateien zusätzlich auf RTD-Nullwerte und RTD-Minimum/-Maximum. Schema und Zeilenanzahl wurden über pyarrow-Metadaten erfasst, die Inhaltsprüfungen mit DuckDB ausgeführt. Es gab keine Fehler bei diesen Abfragen (`data/processed/errors.json` ist leer).

Keine fehlenden Zeitstempel in diesem veröffentlichten Bestand. Bei Revco-Temperaturen bestehen 122 zusätzliche Zeilen mit schon vorhandenem Zeitstempel in 14 Dateien; dies ist nicht identisch mit dem Nachweis komplett identischer Messzeilen. Geräteereignisse: 316 wiederholte Zeitstempel bei Revco und 2 bei Haier; mehrere unterschiedliche Meldungen zur selben Sekunde sind möglich. Bei Haier-Temperaturen keine wiederholten Zeitstempel.

Die Temperaturzeitreihen reichen bei Revco insgesamt von 27.02.2012 bis 01.05.2023 und bei Haier von 16.11.2021 bis 28.03.2023, jeweils abhängig vom Gerät. Diese Grenzen sind keine kontinuierlichen Beobachtungsdauern. Beispiel 806029: maximale Lücke 54.523.140 Sekunden, also rund 631 Tage. Der Gerätevergleich ohne Berücksichtigung solcher Expositionen ist verzerrt. Der beigefügte Autorenbericht `missing_temp_event_files.txt` weist außerdem fehlende Monatsdateien aus; fehlende Monate und Zeitlücken im Parquet messen unterschiedliche Dinge.

Messwerte außerhalb des typischen Kühlbetriebs werden nicht automatisch verworfen. Positive RTD-Werte können z.B. Aufwärmen, Abtauen oder einen Zustand außerhalb des normalen Betriebs zeigen; die Ursache ist aus dem Zahlenwert allein nicht ableitbar. Vollständiger Bericht: `data/processed/measurement_quality.csv`.

## Verknüpfung und Abdeckung

Zuordnung nach sechsstelliger Dateinamen-ID und unverändertem Excel-Kalendertag. Auf Temperaturebene wird kein weiterer Uhrenoffset addiert. Separate Ereignisdateien erhalten den Offset aus `time_offsets.csv`. Unbekannte Zeitzone, mögliche Uhrdrift und Fehlerbeginn bleiben Unsicherheiten.

- 39 von 46 Kalendertagen haben mindestens einen Temperaturmesspunkt.
- 35 Einträge besitzen mindestens einen Messpunkt im Siebentagefenster davor; 33 im Siebentagefenster danach.
- Bei 29 Einträgen existieren Messpunkte in beiden Fenstern.
- Diese Kriterien belegen ausdrücklich keine vollständige oder vergleichbare Messabdeckung. Der Ereignistag wird aus beiden Fenstern ausgeschlossen.

Die Publikation nennt 42 gelabelte Einträge nach vier Fällen ohne Daten. Die eigene Kalendertagsprüfung darf damit nicht gleichgesetzt werden: Weitere Tage sind leer, während eine uneingeschränkte Nächster-Messpunkt-Zuordnung auch über Lücken hinweg Labels erzeugen kann. Einträge werden im Dashboard nicht an einen weit entfernten Messpunkt verschoben.

Demo-Beispiel 806279, 28.06.2022: RTD-Vorherfenster 21.–27.06. umfasst 2.869 Messpunkte mit Mittelwert −64,01 °C, Nachherfenster 29.06.–05.07. 10.075 Punkte mit Mittelwert −79,90 °C. Dies ist ein beschreibender Unterschied bei ungleicher Abdeckung; daraus folgt keine Schätzung der Reparaturwirkung und keine gesicherte Erkennung des Fehlerbeginns.

## Quellenkonflikte und Grenzen

Drei Excel-Einträge widersprechen der Autoren-CSV hinsichtlich Datum oder Fehlertext: 806030 am 30.08.2022, 806031 am 03.02.2023 und 808783 am 14.09.2021. Die gezielte Serviceberichtprüfung und zwei Rohdatenstichproben sind in [repository_pruefung.md](repository_pruefung.md) dokumentiert. Besonders kritisch: Unit-Name-Konflikt 806018/806022 und Positionsjoin bei Haier. Unveränderte Parquets sind Autorenprodukte, keine vollständig unabhängig rekonstruierte Wahrheit.

Serviceberichte, Serviceeinträge, Geräteereignisse, Fehlerkategorien und unabhängige Ausfälle sind getrennte Einheiten. Ein Eintrag kann mehrere Komponenten und mehrere Termine betreffen. Wiederholte Einträge derselben Kategorie können denselben ungelösten Zustand beschreiben. Geräte ohne registrierten Bericht gelten nicht als verifiziert gesund. Keine belastbaren Wiederholungswahrscheinlichkeiten, Ausfallraten oder kausalen Effekte werden angegeben. Die 181 Millionen Messzeilen sind keine 181 Millionen unabhängigen Beobachtungen.

Offen: vollständige manuelle Berichtprüfung; explizite Ereignisepisoden und Datumsintervalle; Geräteidentität; Uhrenqualität; gleichzeitige Betriebsänderungen, Türöffnungen und Abtauphasen; Mindestabdeckung für belastbar vergleichbare Fenster. Erst nach dieser Prüfung sind Modellierungs- und Risikofragen sinnvoll.
