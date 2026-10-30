# PostgreSQL, Serviceberichte und Messdateien

Stand 30.10.2026. Weiterentwicklung des bestehenden Projekts.

| Datei | Aufgabe |
|---|---|
| `app.py` | Konfiguration, Daten laden, vier Bereiche zusammenführen |
| `servicepulse/ui/` | Getrennte Übersicht, Betriebsanalyse, Qualität sowie gemeinsame Darstellung und Servicefilter |
| `servicepulse/management.py` | Geräte suchen/anlegen, Berichte erfassen/bearbeiten, Historie und ähnliche Fälle |
| `servicepulse/database.py` | SQLAlchemy-Verbindung aus lokalem Geheimnis |
| `servicepulse/models.py` | Tabellen, Beziehungen und Versionsprüfung |
| `servicepulse/repository.py` | Erstimport, PostgreSQL-Abfragen, Transaktionen, Geräte und Dateiregister |
| `migrations/versions/0001…0003` | Alembic-Schemaänderungen, Herkunftsschutz, Audit, veröffentlichte Dateiduplikate |
| `scripts/prepare_database.py` | Normalstart prüfen; Erstvorbereitung, Migration, Synchronisation und Dump ausdrücklich getrennt |
| `servicepulse/faults.py` | Excel-Referenz lesen, Kennzahlen, Quellen- und Kontrollblattvergleich |
| `servicepulse/measurements.py` | Begrenzte DuckDB-Parquet-Abfragen und Qualitätsprüfung |
| `servicepulse/case_review.py` | Messlücken, warme Werte und originale State-Bits bei 806279 prüfen |
| `servicepulse/presentation.py` | Deutsche Anzeigen, Diagramme, CSV und sichtbare Linienlücken |
| `servicepulse/imports.py` | Format-, ID-, Zeitstempel- und Duplikatprüfung von Parquet-Uploads |
| `servicepulse/research.py` | Forschungsfrage, Filter, Falltexte, Messabdeckung und Prüfnachweise |
| `scripts/check_local.py` | Excel ↔ PostgreSQL-Originale ↔ historische DuckDB-Kopie ↔ Dateiregister |
| Übrige Forschungs-/Buildskripte | Bewusst erhaltene Quellenprüfung und Reproduktion; kein normaler App-Start |

## Speicherung und Datenfluss

PostgreSQL speichert `devices`, `categories`, `sources`, `service_reports`, `service_actions`, `measurement_files`, `audit_log` und `alembic_version`. Die 46 historischen Berichte besitzen Datei-Prüfsumme, Quellblatt, Quellzeile und eine unveränderliche Original-JSON zusätzlich zur aktuellen Arbeitsfassung. Neue Berichte tragen `manual`, Forschungsberichte `research`. Historische Statuswerte wurden nicht erfunden: „nicht angegeben“.

Ein Advisory-Lock serialisiert Importe und Schreibvorgänge. Eindeutige Import- und Anforderungsschlüssel verhindern Wiederholungen. Eine geänderte Excel wird nicht still erneut importiert. Bericht und Maßnahme werden gemeinsam transaktional gespeichert. Ein Datenbanktrigger protokolliert jede Berichtsversion samt Maßnahme, Vorher/Nachher, Bearbeiter, Zeit und Grund. Die Versionsprüfung verhindert das Überschreiben einer inzwischen geänderten Fassung. Trigger schützen Originalherkunft und Löschung; die Anwendungsrolle kann vorhandene Auditzeilen nicht ändern. Der Bearbeitertext ist keine authentifizierte Identität.

Die 106 veröffentlichten Parquets mit 181.309.902 Mess-/Meldungszeilen bleiben unverändert unter `data/raw`. PostgreSQL enthält nur Metadaten mit Pfad, SHA-256, Gerät, Zeitraum und Zeilenzahl. DuckDB liest begrenzte Ausschnitte direkt. Die frühere DuckDB-Servicekopie bleibt historische Prüfreferenz und ist keine operative Servicequelle mehr. SQLite dient ausschließlich zum Lesen eines originalen Haier-Rohdatenformats.

Bei Forschungsgeräten bezeichnet die vorbelegte Modellangabe zunächst die aus dem veröffentlichten Messdateiordner bekannte Herstellergruppe Revco/Haier; sie ist keine unabhängig validierte individuelle Modellnummer. Für neue Geräte kann eine bekannte konkrete Modellbezeichnung erfasst werden.

## SQL und Berechnung

SQLAlchemy erzeugt parametrisierte Abfragen. Der kleine Servicebestand wird aus PostgreSQL geladen; darauf arbeiten die bisherigen pandas-Filter und Kennzahlen, einschließlich neuer Berichte. Fachlich entsprechen die Abfragen beispielsweise:

```sql
SELECT r.*, c.code, s.name
FROM service_reports AS r
JOIN categories AS c ON c.id = r.category_id
JOIN sources AS s ON s.id = r.source_id
ORDER BY r.id;

SELECT device_id, count(*) AS serviceeintraege
FROM service_reports GROUP BY device_id;

SELECT * FROM audit_log WHERE report_id = :report_id ORDER BY version;
```

DuckDB behält die bisherigen zeitlich begrenzten Abfragen bei:

```sql
SELECT date_trunc('hour', Datetime) AS time,
       avg(RTD), min(RTD), max(RTD), count(RTD)
FROM read_parquet(?)
WHERE Datetime >= ? AND Datetime < ?
GROUP BY 1 ORDER BY 1;
```

Vergleichsfenster schließen den Servicetag aus. Stunden mit mindestens einem gültigen Punkt sind keine vollständigen Betriebsstunden. Lücken werden nicht interpoliert; `connectgaps=False`. State ist ein Bitcode und keine zu mittelnde Temperatur.

## Herkunft und Grenzen

Wissenschaftliche Daten und Autorenannotationen stammen aus Huang et al. (2023). Eigene Entwicklungen sind Datenmodell, Migrationen, Rechte, Transaktionen, Audit, Importregeln, Abfragen und Oberfläche. Autorenquellcode wird weder importiert noch ungeprüft kopiert. [Lizenzen](lizenzen_herkunft.md), [Literatur](literatur.md), [Professorenanforderungen](professor_anforderungen.md).

Die veröffentlichten Ereignisdateien 806267/806281 sind byteidentisch. Beide Originalzuordnungen bleiben als prüfbedürftiger Quellenbefund erhalten. Neue identische Uploads werden abgewiesen. Eine sechsstellige ID im Dateinamen beweist allein noch nicht die tatsächliche Geräteidentität.

Technische Referenzen: [SQLAlchemy-Versionierung](https://docs.sqlalchemy.org/en/20/orm/versioning.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [PostgreSQL initdb](https://www.postgresql.org/docs/17/app-initdb.html).
