# Professorengespräch am 03.11.2026

**Aktualisiert am 30.10.2026:** Vier Hauptbereiche und PostgreSQL. Zusätzlich unter Geräte & Serviceberichte die Erfassungsmaske und vorhandene Historie zeigen. Für eine Live-Erfassung nur einen tatsächlich vorliegenden Bericht verwenden; keine erfundenen Forschungsbefunde anlegen.


Termin laut Projektvorgabe: 10:30 Uhr, C7-15, Prof. Dr. Henrik Blunck. Vorführung etwa fünf bis sieben Minuten. Keine rückwirkende Tätigkeitsaufzeichnung.

## Vor der Vorführung

`ServicePulse.code-workspace` in VS Code öffnen, vorhandene `.venv` verwenden und das Dashboard mit F5 oder `start.cmd` starten. Browser: http://127.0.0.1:8501 . Nur eine Instanz auf demselben Port verwenden. Links **Alle Filter zurücksetzen** wählen: alle Geräte, alle Kategorien, ganzer Zeitraum. Die Auswahlfelder enthalten dann keine langen Listen vorausgewählter Chips.

Optional vor dem Gespräch, nicht während des Vortrags:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/testlauf_postgresql.xml
.\.venv\Scripts\python.exe scripts/check_local.py | Set-Content -Encoding utf8 docs/lokale_pruefung.json
```

Die Forschungsübersicht zeigt nur ein zum Code-Stand passendes Testprotokoll und einen zur Excel sowie den Parquet-Dateimetadaten passenden lokalen Datenabgleich als aktuell an. Prüfstatus und Resultate nicht ohne erfolgreichen Lauf behaupten. Die Protokolle sind lokale Nachweise und werden nicht mit allen Maschinenpfaden veröffentlicht.

## Ablauf

| Zeit | Zeigen | Kernaussage |
|---|---|---|
| 0:00–0:50 | **Datenqualität & Forschung → Forschungsfrage, Ergebnisse und Kontrollen**, Abschnitte 1–4 | Ziel ist nachvollziehbare Aufbereitung und interaktive deskriptive Untersuchung historischer Serviceeinträge, Temperaturen und Datenlücken. Die Frage ist vorläufig und mit dem Betreuer abzustimmen. |
| 0:50–1:30 | Datenquellen und Übersicht | 46 Serviceeinträge an 24 Geräten; 106 veröffentlichte Parquet-Dateien für 53 Geräte. Mess-/Meldungszeilen sind keine unabhängigen Fehlerereignisse. |
| 1:30–2:15 | **Übersicht**, Servicefilter | 11 Geräte haben mehrere Einträge, 5 Original-Gerät/Kategorie-Kombinationen wiederholen sich. Rohhäufigkeiten sind ohne vergleichbare Beobachtungszeiten keine Ausfallraten. |
| 2:15–3:50 | **Betriebsanalyse & Vergleiche → Beispiel: Temperaturveränderung** | Gerät 806279, 28.06.2022, RTD, sieben Tage. Quelle und Excel-Zeile zeigen. Vorher −64,01 °C bei 2.869 Punkten; nachher −79,90 °C bei 10.075 Punkten. 49/168 gegenüber 168/168 Stunden enthalten mindestens einen Messwert. Der Servicetag selbst hat 1.440 gültige Punkte und ist aus den beiden Vergleichsmittelwerten ausgeschlossen. |
| 3:50–4:40 | **Beispiel: Messlücke** | Gerät 806030, 28.01.2015: 24 Punkte am Servicetag, aber null Punkte in beiden Siebentagefenstern. Es gibt keinen berechenbaren Vorher-Nachher-Unterschied. Nicht auf weit entfernte Werte ausweichen. |
| 4:40–5:40 | **Datenqualität & Forschung** und **Datenqualität & Forschung → Forschungsfrage, Ergebnisse und Kontrollen** | 39/46 Tage mit mindestens einem Punkt sind nicht vollständig abgedeckt. Null fehlende Zeitwerte in vorhandenen Zeilen schließen große Lücken nicht aus. Kategorienkontrolle gegen Excel und Quellenwidersprüche erläutern. |
| 5:40–6:30 | VS Code: `repository.py`, `measurements.py`; Anforderungen und nächste Schritte | PostgreSQL speichert Geräte, Berichte, Quellen und Änderungshistorie; DuckDB fragt Parquet direkt ab. SQLite ist nur ein originales Rohdatenformat. Nächste Schritte: Episoden/Zeiten/IDs klären, Mindestabdeckung definieren, Literatur vertiefen. Kein Risikomodell als erledigtes Praxisphasenergebnis behaupten. |

Bei einer Rückfrage zu Quellen statt des Messlückenfalls **Beispiel: Datumswiderspruch** wählen: 806031, Excel 03.02.2023 gegenüber Autorenliste/Auftragsdatum 02.03.2023; im bereits geprüften Bericht stehen weitere Bearbeitungsdaten im März. Diese Termine sind nicht automatisch der Fehlerbeginn. Die Excel bleibt unverändert.

## Formulierungen für die Diskussion

- „Die Temperatur ist in den beobachteten Nachherwerten im Durchschnitt niedriger. Wegen Lücken, Betriebsänderungen und unbekanntem Fehlerbeginn ist das kein Nachweis einer Reparaturwirkung.“
- „Die 39 Tage besitzen mindestens einen Punkt. Im Fall mit 24 Punkten sehen wir, warum diese binäre Kennzahl allein zu wenig ist.“
- „Die Messwerte werden nach Punkten gewichtet. Doppelte Zeitstempel können deshalb mehrfaches Gewicht erhalten. Sie wurden nicht ohne fachliche Regel gelöscht.“
- „Der wissenschaftliche Erkenntnisgewinn liegt auch darin, nachvollziehbar festzustellen, welche Vergleiche mit den verfügbaren Daten überhaupt möglich sind.“

Erfüllungsstand der acht Anforderungen: [professor_anforderungen.md](professor_anforderungen.md). Zeitplan: [zeitplan.md](zeitplan.md). Die Dokumentation ersetzt keine Freigabe des Themas oder Abnahme durch den Betreuer.
