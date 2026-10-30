"""Ordnet Qualität, Forschungsfrage und Quellnachweise ein."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from servicepulse.faults import category_control, metrics, quality
from servicepulse.presentation import (
    category_label,
    display_frame,
    german_number,
)
from servicepulse.research import (
    QUESTION,
    inputs_fingerprint,
    read_test_report,
)
from servicepulse.ui.common import table


def render_quality(
    root: Path,
    df: pd.DataFrame,
    original_df: pd.DataFrame,
    files: pd.DataFrame,
    file_errors: list[dict],
    conflicts: pd.DataFrame | None,
) -> None:
    """Ordnet Qualität, Forschungsfrage und Quellnachweise ein."""
    source = root / "fault_summary_R1.xlsx"
    temperatures = files[files.kind.eq("temp")]
    st.subheader("Wie belastbar ist die Datengrundlage?")
    st.caption(
        "Diese Qualitätsübersicht bezieht sich auf den gesamten lokalen Datenbestand, unabhängig von den Servicefiltern."
    )
    audit_path = root / "data/processed/measurement_quality.csv"
    coverage_path = root / "data/processed/event_coverage.csv"
    audit = None
    if not files.empty and audit_path.exists():
        snapshot = pd.read_csv(audit_path, dtype={"device_id": "string"})
        same_files = set(snapshot.path) == set(files.path)
        fresh = all(
            (Path(path).stat().st_mtime <= audit_path.stat().st_mtime for path in files.path)
        )
        if same_files and fresh:
            audit = snapshot
        else:
            st.warning(
                "Der gespeicherte Messdatenbericht passt nicht mehr zum aktuellen Dateibestand. Bitte den Qualitätsbericht aktualisieren; alte Summen werden nicht als aktuell angezeigt."
            )
    coverage = None
    if not files.empty and coverage_path.exists():
        snapshot = pd.read_csv(coverage_path, dtype={"device_id": "string"})
        current_keys = set(
            zip(
                original_df.source_row,
                original_df.device_id,
                original_df.event_date.dt.strftime("%Y-%m-%d"),
            )
        )
        saved_keys = set(zip(snapshot.source_row, snapshot.device_id, snapshot.date))
        if (
            current_keys == saved_keys
            and set(snapshot.device_id).issubset(set(temperatures.device_id))
            and (coverage_path.stat().st_mtime >= source.stat().st_mtime)
        ):
            coverage = snapshot
        else:
            st.warning(
                "Die gespeicherte Messabdeckung passt nicht zur aktuellen Servicequelle oder es fehlen zugehörige Messdateien. Bitte die Abdeckung erneut berechnen."
            )
    areas = st.columns(4)
    areas[0].metric(
        "Servicetage mit Messpunkten",
        f"{int((coverage.day_rows > 0).sum())} / {len(coverage)}"
        if coverage is not None
        else "Nicht geprüft",
        help="Mindestens ein Messpunkt am dokumentierten Tag. Das ist keine Aussage über vollständige Tagesabdeckung.",
    )
    areas[1].metric(
        "Fehlende Zeitwerte",
        german_number(audit.null_times.sum()) if audit is not None else "Nicht geprüft",
        help="Zeilen ohne gültigen Zeitwert im gespeicherten Prüfbericht über Mess- und Meldungsdateien.",
    )
    temp_audit = audit[audit.kind.eq("temp")] if audit is not None else None
    areas[2].metric(
        "Mehrfache Temperatur-Zeitstempel",
        german_number(temp_audit.repeated_timestamps.sum())
        if temp_audit is not None
        else "Nicht geprüft",
        help="Zusätzliche Temperaturzeilen mit einem bereits vorhandenen Zeitpunkt. Das beweist nicht, dass alle Messwerte identisch sind.",
    )
    areas[3].metric(
        "Quellenwidersprüche",
        str(len(conflicts)) if conflicts is not None else "Nicht geprüft",
        help="Excel-Einträge mit anderem Fehlertext oder ohne passenden Eintrag am selben Tag in der Autorenliste.",
    )
    st.markdown("#### Was bedeuten diese Qualitätszahlen fachlich?")
    st.markdown(
        "- **Mindestens ein Messpunkt ist keine vollständige Abdeckung.** Ein Servicetag kann nur wenige Werte enthalten; Vorher- und Nachherfenster können leer sein.\n- **Null fehlende Zeitwerte bedeutet nicht null Messlücken.** Jede vorhandene Zeile kann ein Datum besitzen, während zwischen diesen Zeilen Monate ohne Aufzeichnung liegen.\n- **Wiederholte Zeitstempel können Mittelwerte beeinflussen.** Mehrfach vorhandene Zeilen erhalten im messpunktgewichteten Mittel mehrfaches Gewicht. Sie bleiben erhalten, bis eine fachlich begründete Duplikatregel feststeht.\n- **Mehrfach dokumentiert bedeutet nicht mehrfach unabhängig ausgefallen.** Berichte können denselben ungelösten Zustand oder verschiedene Maßnahmen zum selben Fall beschreiben."
    )
    if coverage is not None:
        both = int(((coverage.before_rows > 0) & (coverage.after_rows > 0)).sum())
        st.info(
            f"Für {both} von {len(coverage)} Einträgen gibt es Messpunkte sowohl in den sieben Tagen vor als auch nach dem Servicetag. Lücken und ungleiche Messpunktzahlen bleiben möglich."
        )
    if temp_audit is not None:
        gap_days = temp_audit.max_gap_seconds.max() / 86400
        st.warning(
            f"Messlücken beachten: Die größte beobachtete Lücke in einer Temperaturdatei beträgt rund {german_number(gap_days)} Tage. Zeiträume ohne Werte werden nicht aufgefüllt."
        )
    st.markdown("#### Bekannte Grenzen")
    st.write(
        "Servicedaten besitzen keine verlässliche Uhrzeit. Bei Gerät 806031 widersprechen sich Datumsangaben; bei 806030 und 808783 unterscheiden sich Beschreibungen. Eine Rohdatenstichprobe im Ordner 806018 nennt Geräte-ID 806022. Diese Widersprüche werden nicht automatisch korrigiert."
    )
    st.caption(
        "Zusätzlicher Quellenbefund: Die veröffentlichten Ereignisdateien der Geräte 806267 und 806281 sind byteidentisch. Beide ursprünglichen Zuordnungen bleiben erhalten und müssen fachlich geprüft werden; sie belegen keine unabhängigen Ereignisverläufe."
    )
    if conflicts is not None:
        table(conflicts[["device_id", "event_date", "reference_status"]], key="source_conflicts")
    else:
        st.info(
            "Die Autorenliste liegt lokal nicht vor. Der automatische Quellenvergleich ist daher nicht verfügbar."
        )
    with st.expander("Messabdeckung je Serviceeintrag"):
        st.caption(
            "Messpunktzahlen sind keine Betriebsstunden. Ein leerer Tag kann auch zwischen vorhandenen Aufzeichnungen liegen."
        )
        if coverage is not None:
            compact = display_frame(
                coverage[["device_id", "date", "day_rows", "before_rows", "after_rows"]]
            ).rename(
                columns={
                    "Messpunkte am Servicetag": "Am Servicetag",
                    "Messpunkte vor dem Servicetag": "7 Tage davor",
                    "Messpunkte nach dem Servicetag": "7 Tage danach",
                }
            )
            st.dataframe(compact, hide_index=True, width="stretch", height=300)
        else:
            st.info(
                "Kein aktueller Bericht zur Messabdeckung verfügbar. Die Daten können trotzdem direkt in der Messansicht abgefragt werden."
            )
    with st.expander("Qualität der Serviceübersicht und Kategorienkontrolle"):
        service_quality = quality(original_df).copy()
        service_quality["Prüfung"] = service_quality["Prüfung"].replace(
            {
                "Fehlende Werte: Fault categories": "Fehlende Fehlerkategorien",
                "Fehlende Werte: freezer_id": "Fehlende Geräte-IDs",
                "Fehlende Werte: registered_date": "Fehlende Servicedaten",
                "Fehlende Werte: main_fault": "Fehlende Fehlerbeschreibungen",
                "Kategorie Data missing": "Einträge der Originalkategorie „Messdaten fehlen“",
                "Kategorie No fix": "Einträge ohne dokumentierte Behebung",
            }
        )
        st.dataframe(service_quality, hide_index=True, width="stretch")
        table(category_control(source, original_df))
    with st.expander("Technische Details · vollständige Prüfberichte und Originalwerte"):
        st.caption(
            "Feldüberschriften sind als Lesehilfe übersetzt. Unveränderte Originalfelder stehen im CSV-Export und in den lokalen Berichten zur Verfügung."
        )
        table(files, height=260)
        if audit is not None:
            table(audit, height=300)
            st.download_button(
                "Vollständigen Messdatenbericht als CSV herunterladen",
                audit.to_csv(index=False).encode("utf-8-sig"),
                "servicepulse_datenqualitaet.csv",
                "text/csv",
                key="export_quality",
            )
        if coverage is not None:
            table(coverage, height=300)
        if conflicts is not None:
            st.dataframe(conflicts, hide_index=True, width="stretch", height=200)
    if file_errors:
        st.error(
            f"{len(file_errors)} Datei(en) konnten nicht gelesen werden. Sie sind nicht Teil der Messauswahl."
        )
        with st.expander("Technische Details · nicht lesbare Dateien"):
            table(pd.DataFrame(file_errors))
    if audit is None:
        st.caption(
            "Prüfberichte lassen sich in VS Code über die Aufgabe „Datenbank und Qualitätsberichte aktualisieren“ erstellen. Das ist für die normale Filterbedienung nicht nötig."
        )
    research = st.expander("Forschungsfrage, Ergebnisse und Kontrollen")
    method = st.expander("Wissenschaftliche Methodik, Quellen und Lizenzen")
    with research:
        st.subheader("Forschungsfrage & Ergebnisse")
        st.caption(
            "Dieser Bereich beschreibt den gesamten vorhandenen Datenbestand, unabhängig von den Servicefiltern. Die Forschungsfrage ist vorläufig und mit Prof. Blunck abzustimmen."
        )
        st.markdown("#### 1 · Forschungsfrage")
        st.info(QUESTION)
        st.markdown("#### 2 · Verwendete Datenquellen")
        full = metrics(original_df)
        st.write(
            f"Die Service-Excel enthält {full['entries']} Einträge an {full['devices']} Geräten. Lokal sind {len(files)} lesbare Mess- und Meldungsdateien für {files.device_id.nunique()} Geräte verfügbar. Die Service-Excel, Autorenlisten und publizierten Parquets stammen aus dem Datensatz von Huang und Mitautoren (2023). Serviceberichte werden als separate Originalquelle zur Klärung von Widersprüchen verwendet."
        )
        st.markdown("#### 3 · Untersuchungsmethode")
        st.write(
            "Originalwerte erhalten, Kennungen und Datumsfelder nachvollziehbar aufbereiten, Servicezeilen deskriptiv zählen, Messreihen nach Geräte-ID und Kalendertag untersuchen. DuckDB fragt die Parquets zeitlich begrenzt ab. Vorher-Nachher-Mittelwerte sind messpunktgewichtet und schließen den Servicetag aus. Lücken bleiben leer."
        )
        st.markdown("#### 4 · Messbare Zielgrößen")
        st.markdown(
            "Eintragszahl · betroffene Geräte · Kategorienhäufigkeiten · mehrfache Gerät/Kategorie-Kombinationen · Messpunkte vor, am und nach einem Servicetag · Stunden mit/ohne Messpunkte · Temperaturdurchschnitt, Minimum und Maximum. Diese Größen beschreiben Dokumentation und Beobachtung; sie messen keine bewiesenen unabhängigen Ausfälle."
        )
        st.markdown("#### 5 · Vergleichs- und Kontrollverfahren")
        control = category_control(source, original_df)
        control_ok = not control.empty and bool(control.matches.all())
        checks = [
            {
                "Kontrolle": "Berechnete Kategorien gegen zweites Excel-Blatt",
                "Stand": f"{int(control.matches.sum())} von {len(control)} Gruppen stimmen überein"
                if not control.empty
                else "Kontrollblatt nicht vorhanden",
                "Bedeutung": "Rechnerische Konsistenz, keine Validierung der tatsächlichen Fehlerursache.",
            },
            {
                "Kontrolle": "Serviceeinträge gegen Messdaten",
                "Stand": f"{int((coverage.day_rows > 0).sum())} von {len(coverage)} Tagen mit Messpunkten"
                if coverage is not None
                else "Aktueller Abdeckungsbericht fehlt",
                "Bedeutung": "Ein Treffer belegt nur einzelne Messungen; Zeitfenster separat prüfen.",
            },
            {
                "Kontrolle": "Excel gegen Autoren-CSV",
                "Stand": f"{len(conflicts)} Einträge mit Abweichung"
                if conflicts is not None
                else "Autorenliste fehlt",
                "Bedeutung": "Keine automatische Umdeutung oder Korrektur von Datum und Fehlertext.",
            },
        ]
        st.dataframe(pd.DataFrame(checks), hide_index=True, width="stretch", key="research_checks")
        with st.expander("Nachvollziehen: Kategorienhäufigkeiten und Excel-Kontrolle"):
            table(control)
            if not control.empty and (not control_ok):
                st.warning(
                    "Mindestens eine Kontrollsumme weicht ab. Dies muss vor der fachlichen Interpretation geklärt werden."
                )
        run = read_test_report(root)
        if run is None:
            st.caption(
                "Für diesen Code-Stand liegt hier noch kein aktuelles Testprotokoll vor. Reproduktion: python -m pytest -q --junitxml=docs/testlauf_praxis.xml"
            )
        else:
            st.write(
                f"Aktuelles automatisiertes Prüfprotokoll: {run['passed']} bestandene Tests, {run['skipped']} übersprungen, {run['failures'] + run['errors']} fehlgeschlagen. Dazu gehört ein SQL-/pandas-Vergleich für reale Stundenaggregate, sofern die optionale Messdatei vorliegt."
            )
        verification_path = root / "docs/lokale_pruefung.json"
        try:
            verification = (
                json.loads(verification_path.read_text(encoding="utf-8-sig"))
                if verification_path.exists()
                else {}
            )
            current = verification.get("status") == "ok" and verification.get(
                "inputs_fingerprint"
            ) == inputs_fingerprint(source, files)
        except (OSError, ValueError, KeyError):
            current = False
        if current:
            checked = pd.Timestamp(verification["checked_at"]).tz_convert("Europe/Budapest")
            st.success(
                f"Lokaler Datenabgleich erfolgreich, ausgeführt am {checked:%d.%m.%Y um %H:%M}: Originalwerte in PostgreSQL, Excel-Referenz, historische DuckDB-Kopie und Messdateiregister stimmen überein."
            )
        else:
            st.caption(
                "Kein zum aktuellen Dateistand passendes Abgleichprotokoll verfügbar. Den schreibgeschützten Datenabgleich mit python scripts/check_local.py ausführen; Prüfprotokolle sind keine Garantie fachlich richtiger Labels."
            )
        st.markdown("#### 6 · Tatsächlich ermittelte Ergebnisse")
        st.write(
            f"{full['entries']} Serviceeinträge an {full['devices']} Geräten; {full['devices_multiple_entries']} Geräte mit mehreren Einträgen und {full['repeated_device_category_pairs']} wiederholte Original-Gerät/Kategorie-Paare."
        )
        category_counts = original_df.category.value_counts()
        if not category_counts.empty:
            st.write(
                f"Die häufigste Originalkategorie ist {category_label(category_counts.index[0])} mit {int(category_counts.iloc[0])} Einträgen. Das ist eine Dokumentationshäufigkeit, kein Anteil unabhängig ausgefallener Geräte."
            )
        if coverage is not None:
            st.write(
                f"{int((coverage.day_rows > 0).sum())} von {len(coverage)} Servicetagen haben mindestens einen Temperaturmesspunkt. Bei {int(((coverage.before_rows > 0) & (coverage.after_rows > 0)).sum())} Einträgen gibt es Messpunkte in beiden angrenzenden Siebentagefenstern. Vollständige Abdeckung folgt daraus nicht."
            )
        if temp_audit is not None:
            st.write(
                f"Der aktuelle Messdatenbericht enthält {int(temp_audit.repeated_timestamps.sum())} zusätzliche Temperaturzeilen mit bereits vorkommendem Zeitstempel. Diese werden nicht stillschweigend entfernt."
            )
        st.caption(
            "Die ausgewählten Fallbeispiele und ihre konkreten Temperatur- und Abdeckungswerte werden unter „Betriebsanalyse & Vergleiche“ direkt aus den Messdateien berechnet."
        )
        st.markdown("#### 7 · Wissenschaftliche Einschränkungen")
        st.write(
            "Wenige dokumentierte und nicht notwendigerweise unabhängige Fälle, unsichere Servicezeiten, Quellenwidersprüche, unterschiedliche Beobachtungsdauern und lange Messlücken begrenzen die Aussagekraft. Geräte ohne Servicebericht sind nicht als gesund validiert. Weder Ausfallwahrscheinlichkeiten noch Reparaturwirkungen oder Prognosegenauigkeiten werden behauptet."
        )
        st.markdown("#### 8 · Noch offene Fragen")
        st.markdown(
            "- Welche Berichte gehören zu derselben Serviceepisode, welche zu unabhängigen Defekten?\n- Welche Zeitpunkte bezeichnen Auftrag, Reparatur oder tatsächlichen Fehlerbeginn?\n- Wie lassen sich Geräteidentität, historische Uhren und gleiche Beobachtungsbedingungen absichern?\n- Welche Mindestabdeckung ist für sinnvolle deskriptive Vergleiche erforderlich?\n- Können später einfache Referenzverfahren auf vergleichbaren Betriebsfenstern geprüft werden? Diese Verfahren und eine mögliche Risikofrage gehören zur Bachelorperspektive und sind noch nicht implementiert."
        )
    with method:
        st.subheader("Was diese Anwendung zeigt – und was die Daten erlauben")
        st.markdown(
            "ServicePulse beschreibt historische Betriebswerte und dokumentierte Serviceeinträge. Die Daten stammen aus dem wissenschaftlichen ULT-Datensatz von Huang und Mitautoren (2023), erhoben an Geräten der Dänischen Nationalen Biobank. Es werden keine Ausfälle oder Messwerte simuliert und keine Ausfallwahrscheinlichkeiten vorhergesagt.\n\n**Serviceeintrag und Ausfall sind unterschiedliche Dinge.** Ein Bericht kann mehrere Komponenten oder Termine betreffen. Mehrere Berichte können denselben ungelösten Zustand beschreiben. Ein Gerät ohne Serviceeintrag ist nicht automatisch störungsfrei.\n\n**Zeitangaben sind begrenzt.** Markierungen zeigen den dokumentierten Kalendertag, keinen gesicherten Fehlerbeginn. Die Zeitzone ist nicht eindeutig spezifiziert. Uhrkorrekturen der Autoren werden offengelegt, aber nicht als Nachweis historischer Uhrgenauigkeit behandelt.\n\n**Vergleiche sind beschreibend.** Vorher-Nachher-Werte können sich durch Lücken, unterschiedliche Messpunktzahlen oder veränderte Betriebszustände unterscheiden. Daraus folgt keine bewiesene Reparaturwirkung."
        )
        with st.expander("Deutsche Bezeichnungen und englische Originalkategorien"):
            translation = pd.DataFrame(
                {
                    "Deutsche Bezeichnung": [
                        category_label(v) for v in sorted(df.category.unique())
                    ],
                    "Originalwert": sorted(df.category.unique()),
                }
            )
            st.dataframe(translation, hide_index=True, width="stretch")
            st.caption(
                "„No fix“ wird als „ohne Behebung“ angezeigt. „Data missing“ bleibt eine eigene Autorenkategorie. Übersetzungen sind Lesehilfen, keine neue fachliche Diagnose."
            )
        st.markdown(
            "#### Herkunft und Nutzungsbedingungen\n\n- [Wissenschaftlicher Artikel](https://doi.org/10.1038/s41597-023-02808-6) · Huang und Mitautoren, 2023 · Lizenz CC BY 4.0\n- [Wissenschaftliche Datensammlung](https://doi.org/10.6084/m9.figshare.c.6805332.v1) · Datenlizenz laut Figshare-Metadaten: CC0\n- [Verarbeitungscode der Autoren](https://lab.compute.dtu.dk/taohu/ult-freezers-labelled-dataset-sci-data) · separate Referenz; keine ausdrückliche Codelizenz im geprüften Stand gefunden\n\nDie eigenen Entwicklungsleistungen umfassen die Datenprüfung, Excel-Aufbereitung, begrenzte SQL-Abfragen mit DuckDB, Visualisierung und Benutzerführung. Die veröffentlichten Messdateien und Autorenannotationen bleiben als wissenschaftliche Quellen erkennbar."
        )
        with st.expander("Technische Methodik und lokale Dokumentation"):
            st.write(
                "PostgreSQL ist die maßgebliche Quelle der Serviceberichte. Die Original-Excel bleibt unveränderte Forschungsreferenz; ihre 46 Zeilen sind mit Prüfsumme, Blatt und Zeile importiert. Eigene Berichte sind separat gekennzeichnet. SQLAlchemy und Alembic kontrollieren Zugriff und Schemaänderungen. Große Messreihen bleiben in Parquet-Dateien und werden zeitlich begrenzt mit DuckDB abgefragt. Die frühere DuckDB-Servicekopie dient nur noch dem historischen Abgleich; neue Berichte und deren Änderungen stehen ausschließlich in PostgreSQL. SQLite wird nur zum schreibgeschützten Lesen originaler Haier-Rohdaten benutzt."
            )
            st.code(
                "docs/datenanalyse.md\ndocs/repository_pruefung.md\ndocs/lizenzen_herkunft.md\ndocs/technik_sql.md",
                language=None,
            )
