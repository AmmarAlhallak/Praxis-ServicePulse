# Technische Kurzvorführung in VS Code am 03.11.2026

Für die aktuelle fünf- bis siebenminütige Vorführung mit den neuen Fallbuttons siehe [Praxis-Demo](praxis_demo_03_11.md). Die technischen Startschritte unten gelten weiterhin.

Termin laut Vorgabe: 10:30 Uhr in C7-15. Diese Anleitung ergänzt den fachlichen [Demo-Leitfaden](demo_03_11.md).

## Vorher, etwa zwei Minuten

`ServicePulse.code-workspace` in VS Code öffnen. Prüfen, dass die lokale `.venv` ausgewählt ist. Im Terminal aus dem Projektordner:

```powershell
.\.venv\Scripts\python.exe scripts/check_local.py
.\.venv\Scripts\python.exe -m pytest -q
```

Beide Befehle müssen erfolgreich enden. Eine bereits laufende Instanz weiterverwenden; ansonsten F5 → **ServicePulse: Dashboard (Streamlit)**. In der Debugging-Konsole erscheint `http://127.0.0.1:8501`; diese Adresse im Browser öffnen. Kein Download und kein voller Datenbank-Neuaufbau während der Vorführung erforderlich.

## Vorführung, fünf bis sieben Minuten

| Zeit | Aktion | Erklärung |
|---|---|---|
| 0:00–1:00 | VS-Code-Explorer: `app.py`, `servicepulse/`, `data/` zeigen | „Die Oberfläche und Verarbeitung sind getrennt. Alle Quellen und Ergebnisse liegen lokal; die vorhandene Architektur wurde erhalten.“ |
| 1:00–2:00 | `storage.py` und `measurements.py` öffnen | „DuckDB speichert kleine Service-/Metadatentabellen und fragt große Parquets direkt per SQL ab. SQLite ist nur ein originales Haier-Eingabeformat und wird schreibgeschützt gelesen.“ |
| 2:00–3:00 | Dashboard-Übersicht, Filter und Geräteanalyse | 46 Serviceeinträge, 24 Geräte. Gerät/Kategorie/Datum kombinieren; Filter zurücksetzen. Einträge sind keine bestätigten unabhängigen Ausfälle |
| 3:00–4:30 | Temperatur & Betrieb: 806279, 28.06.2022, Kammertemperatur (RTD), sieben Tage | Ganze Servicetage markieren; Messlücken offen zeigen. Vorher/Nachher mit unterschiedlichen Stichprobenzahlen erklären; keine Kausalbehauptung |
| 4:30–5:30 | Datenqualität und Kontrollblatt | Quellenwidersprüche und Zeitunsicherheit zeigen. Keine ungeprüfte Korrektur und keine Prognosebehauptung |
| 5:30–6:30 | `check_local.py`, Testresultat und `technik_sql.md` | „Excel und Datenbank wurden inhaltlich abgeglichen; stündliche SQL-Aggregate wurden zusätzlich mit pandas geprüft. Weitere Tests prüfen kombinierte Filter und Diagramme.“ |

Für eine SQL-Erklärung genügt das Beispiel `SELECT ... FROM read_parquet(?) WHERE Datetime >= ? AND Datetime < ? GROUP BY ...` in `technik_sql.md`. Dateipfad und Zeitgrenzen werden gebunden, die Messgröße wird gegen das echte Schema geprüft. Keine zusätzliche Datenbank-Erweiterung in VS Code nötig.

## Technische Entscheidungen in einem Satz

- **Warum Streamlit?** Lokale interaktive Python-App ohne eigenes Frontend-/Serversystem.
- **Warum DuckDB?** Eingebettete SQL-Analyse großer Parquets, ohne sie vollständig in eine zweite Datenkopie zu importieren.
- **Warum pandas zusätzlich?** Die kleine Excel-Servicetabelle lässt sich damit direkt prüfen und filtern; DuckDB ergänzt die großen Zeitreihen.
- **Warum keine SQLite-Anwendungsdatenbank?** Dafür besteht kein zusätzlicher Nutzen; SQLite wird lediglich für das bereits so gelieferte Rohdatenformat gebraucht.
- **Warum `.venv` und feste Anforderungen?** Projektabhängigkeiten sind vom übrigen Windows-System getrennt und nachvollziehbar installiert.
- **Was bleibt offen?** Fachliche Klärung von Gerätekennungen, Serviceepisoden und unsicheren Zeiten; vollständige Rohdatenrekonstruktion. Der technische Prototyp ersetzt diese Prüfungen nicht.

Beenden: Umschalt+F5 beim F5-Start, Strg+C beim Terminal-Start. Falls Port 8501 belegt ist, zuerst die vorhandene Instanz prüfen; nicht mehrere Starts hintereinander auslösen.
