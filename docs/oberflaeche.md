# Deutsche Benutzeroberfläche

Überarbeitung am 29.10.2026 im bestehenden Projekt. Keine Originaldaten wurden verändert oder gelöscht, und es wurden keine Messwerte ergänzt. DuckDB, Excel-Aufbereitung und die SQL-Fensterberechnungen bleiben erhalten.

## Bedienung

Links unter **Serviceauswahl** Geräte, Fehlerkategorien und Servicedatum eingrenzen. Eine leere Auswahl liefert keine Einträge. **Alle Filter zurücksetzen** stellt den Gesamtbestand wieder her. Die vier Hauptkennzahlen müssen dann 46 Serviceeinträge, 24 betroffene Geräte, 11 mehrfach dokumentierte Geräte und 5 wiederholte Gerät/Kategorie-Paare anzeigen.

| Bereich | Inhalt |
|---|---|
| Übersicht | wichtigste Kennzahlen, verständliche Kategorienhäufigkeiten, Bedienhinweise, übersetzte Serviceübersicht und CSV-Export |
| Störungsanalyse | Kategorien mit optionaler Zusammenfassung von „ohne Behebung“, Einträge je Geräte-ID, wiederholte Kombinationen und zeitliche Verteilung |
| Temperatur & Betrieb | Messgerät, Messgröße, Servicetag oder freier Zeitraum, reale Kurve, Mittelwert/Minimum/Maximum und Vorher-Nachher-Vergleich |
| Datenqualität | Messabdeckung, fehlende Zeiten, wiederholte Temperaturzeitstempel, Quellenwidersprüche; weitere Berichte aufklappbar |
| Methodik & Quellen | Bedeutung von Serviceeinträgen, Zeitunsicherheit, Grenzen der Vergleiche, Datenherkunft und Übersetzungstabelle |

Die Servicefilter beeinflussen die verfügbaren Serviceeinträge und Kurvenmarkierungen. Das Messgerät wird ausdrücklich separat gewählt, damit auch die Messdaten von Geräten ohne Servicebericht betrachtet werden können. Diese Trennung steht direkt bei den Filtern.

## Kurze Professor-Demo

1. Übersicht zeigen: 46 / 24 / 11 / 5 und die Erklärung, warum Serviceeinträge keine bestätigten unabhängigen Ausfälle sind.
2. Links die Fehlerkategorie **Kältemittelleckage** auswählen, die Störungsanalyse öffnen und die Auswahl als CSV exportieren. Danach Filter zurücksetzen.
3. **Temperatur & Betrieb** öffnen: Gerät **806279**, **Kammertemperatur (RTD)**, Servicetag **28.06.2022**, sieben Tage, stündliche Zusammenfassung. Das ist auch die Voreinstellung des vorhandenen Datenbestands.
4. Mittelwert, Minimum, Maximum und sichtbare Lücken erklären. Die farbige Fläche umfasst den gesamten Servicetag; sie bezeichnet keinen nachgewiesenen Fehlerbeginn.
5. Vergleich zeigen: vorher 2.869 gültige Messpunkte und rund −64,01 °C, nachher 10.075 Messpunkte und rund −79,90 °C. Auf ungleiche Abdeckung und fehlenden Kausalnachweis hinweisen.
6. **Datenqualität** öffnen: 39/46 Servicetage mit Messpunkten, 122 zusätzliche Temperaturzeilen mit bereits vorkommendem Zeitstempel und drei Excel-/Autorenlisten-Widersprüche. Ganze Prüftabellen bleiben in „Technische Details“ verfügbar.

## Darstellung und Originalwerte

`servicepulse/presentation.py` enthält deutsche Kategorien, Fehlerbeschreibungen, Messgrößen, Einheiten, Tabellenüberschriften und Diagrammgestaltung. Diese Funktionen arbeiten auf Kopien. Die englischen Originalspalten und Originalwerte bleiben in den Quellen und technischen Ansichten unverändert.

Der Service-CSV-Export ergänzt zwei deutsche Lesehilfen und enthält weiterhin sämtliche bisherigen Original- und Herkunftsfelder. Messwert- und Qualitäts-CSV behalten ihre technischen Feldbezeichnungen und berechneten Zahlen zur Nachprüfung. Datumseingaben und dargestellte Datumswerte verwenden TT.MM.JJJJ; Temperaturen sind mit °C und Spannung mit V gekennzeichnet. Unveränderte englische Gerätemeldungen sind bewusst nur in der Expertenansicht sichtbar. Native Dateiauswahl- und Kalenderdialoge sowie einzelne Bedienhilfen des Streamlit-Rahmens können abhängig von Browser-/Systemsprache weiterhin englische Systemtexte enthalten; keine Bibliotheksdateien wurden dafür verändert.

Die Diagramme bleiben interaktiv: Werte mit dem Mauszeiger ablesen, Ausschnitte per Ziehen vergrößern und Legendenlinien anklicken. Die Diagramm-Werkzeugleisten sind für die normale Ansicht ausgeblendet; der CSV-Export erfolgt über eigene deutsche Schaltflächen. Auf schmalen Ansichten öffnet das Pfeilsymbol oben links die Filterleiste.

## Expertenansicht und Import

Lange Dateipfade, genaue Vergleichsfenster, Originalwerte, Meldungslisten und vollständige Qualitätsberichte sind aufklappbar. Im normalen Messbereich werden keine langen Pfade angeboten.

Der Import steht unter **Erweiterte Funktion · Weitere Messdateien importieren**. Der vollständige lokale Forschungsbestand enthält bereits 106 Dateien; für die normale Nutzung ist kein erneuter Import erforderlich. `servicepulse/imports.py` prüft Namen, Format, Zeitstempelspalte, geeignete numerische Messfelder und die 300-MB-Grenze. Speichern erfolgt mit exklusiver Dateierstellung: vorhandene Ziele werden auch bei einer konkurrierenden Anfrage nicht überschrieben. Herkunft, Lizenz und Zeitkonvention zusätzlicher Dateien müssen weiterhin geklärt sein.

## Fachliche und technische Prüfungen

Die Originalkennzahlen und SQL-Aggregate werden durch die bestehenden Tests abgesichert. Neue Tests prüfen Übersetzungsvollständigkeit für die vorhandene Excel, Unverändertheit der Daten, CSV-Originalwerte, deutsche Diagrammlegenden, die vollständige Servicetag-Markierung, sichtbare Messlücken sowie gültige/ungültige Importe und Überschreibschutz.

Ein zusätzlich behobener Auswahlfehler betraf numerische Ereignislisten: Eine DuckDB-Liste wie `BIGINT[]` darf nicht als skalare Messgröße angeboten werden. Die Feldauswahl erkennt jetzt ausschließlich skalare numerische Typen. Temperatur-, Spannungs- und Vorher-Nachher-Berechnungen wurden dabei nicht geändert.

Gespeicherte Messdatenberichte werden nur als aktuell angezeigt, wenn sie zum vorhandenen Dateibestand passen und nicht älter als die Messdateien sind. Die Abdeckung wird mit den tatsächlichen Service-IDs und -Tagen abgeglichen. Unpassende Berichte erhalten einen Aktualisierungshinweis statt alter Summen. Diese UI-Prüfung ersetzt den vollständigen lokalen Datenabgleich nicht.

Start unverändert: `python -m streamlit run app.py` mit der lokalen `.venv`, alternativ F5 oder `start.cmd`. Prüfung: `python -m pytest -q` und `python scripts/check_local.py`. Es ist kein erneuter Forschungsdaten-Download nötig.

Ausgeführte Prüfungen: 29 Tests im vollständigen lokalen Bestand erfolgreich; zusätzlicher Excel-Betrieb ohne lokale Messdateien und Build mit 25 erfolgreichen und vier ausdrücklich übersprungenen optionalen Integrationstests. Der lokale Datenabgleich meldet `ok`. Übersicht, Beispielkurve 806279/28.06.2022 und Qualitätsübersicht wurden im Browser kontrolliert. Bildschirmnachweise: `oberflaeche_uebersicht.png` und `oberflaeche_betrieb.png`. Die vorhandenen Startwege und Originalquelldateien bleiben erhalten.
