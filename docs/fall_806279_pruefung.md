# Nachprüfung 806279 vom 21.06. bis 05.07.2022

Am 30.10.2026 direkt auf `data/raw/Revco/806279_temp.parquet` und `806279_events.parquet` nachgerechnet. Dies sind bereits von den Autoren verarbeitete veröffentlichte Dateien, keine vollständige eigene Rekonstruktion der ursprünglichen Revco-Exporte dieses Geräts.

## Messwerte

- Letzter Punkt vor der großen Lücke: **22.06.2022 10:36:20**. Nächster Punkt: **27.06.2022 10:48:15**. Abstand **432.715 Sekunden**: fünf Tage, elf Minuten und 55 Sekunden. Der Verlauf dazwischen ist unbekannt.
- **145 Werte über +15 °C** am 27.06., zwischen 10:48:15 und 13:12:20. Tagesmaximum **+21,8 °C**, Tagesminimum −80,6 °C. Anschließendes Abkühlen ist in den vorhandenen Werten sichtbar.
- Insgesamt **14.384 Punkte** im Fenster, keine wiederholten Zeitstempel in diesem Fenster. Weitere Lücke: 05.07. zwischen 09:18:20 und 09:24:20, sechs Minuten.
- Excel dokumentiert am 28.06. eine Kältemittelleckage in Stufe 1 (`Refrigerant leakage at stage 1`, Quellzeile 41). Das Tageslabel liefert keinen gesicherten Fehlerbeginn oder Reparaturabschluss.
- Sieben Tage davor: 2.869 Punkte, Mittel −64,01 °C, Minimum −80,7 °C, Maximum +21,8 °C; 49/168 Stunden mit Punkten.
- Sieben Tage danach: 10.075 Punkte, Mittel −79,90 °C, Minimum −81,2 °C, Maximum −65,7 °C; 168/168 Stunden mit Punkten.
- Servicetag: 1.440 Punkte, ausgeschlossen aus beiden Vergleichsmittelwerten.

## Ereignisse und Betriebskennzeichen

`time_offsets.csv` liefert für 806279 **+00:09:20**, Referenz am 25.04.2023. Nur die separate Ereignisdatei wird damit korrigiert. Die Temperaturdatei ist laut Autorenpipeline bereits korrigiert und wird nicht nochmals verschoben.

| Korrigierter Zeitpunkt | Originalmeldung |
|---|---|
| 22.06.2022 10:36:52 | Shutdown |
| 27.06.2022 10:48:09 | Display Power On |
| 27.06.2022 10:48:27 | Power Modes = High Performance |

Die Einschaltmeldung liegt sechs Sekunden vor dem ersten wieder vorhandenen Temperaturpunkt. Weitere Tür- und Zwischenstufentemperaturmeldungen sind vorhanden. Das belegt für sich keine Ursache der Erwärmung.

State-Codes im Fenster: 0 (4.043 Punkte), 1 (1.610), 3 (8.722), 16 (2), 19 (7). Die niedrigsten zwei Bits werden entsprechend der Autorenbeschreibung als Verdichtersignale separat ausgewiesen. Keine vollständige Dekodierung übriger Bits und kein unabhängiger Nachweis tatsächlicher mechanischer Verdichterleistung.

## Einordnung

Lücke und positive Temperaturen sind durch die veröffentlichten Werte gedeckt, kein erfundener Diagrammverlauf. Abschaltung und Einschalten passen zeitlich zur Unterbrechung. Daraus folgen weder ein gesicherter Grund der Lücke noch eine nachgewiesene Reparaturwirkung. Betriebsabsicht, Stromversorgung, Probenzustand, Uhrdrift und vollständiger Serviceablauf sind nicht bestätigt. Ungleiche Messabdeckung begrenzt den Mittelwertvergleich.

Die Grafik unterbricht fehlende Zeitintervalle. Stundenaggregate fassen vorhandene Werte zusammen; die Minutenansicht erlaubt Details. Reproduktion: `servicepulse/case_review.py`, `servicepulse/measurements.py` und `test_real_temperature_gap_warm_values_and_corrected_events`.
