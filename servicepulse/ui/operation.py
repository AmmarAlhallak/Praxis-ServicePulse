"""Zeigt vorhandene Messdaten und Vergleiche ohne Lückenfüllung."""

from pathlib import Path

import pandas as pd
import streamlit as st

from servicepulse import repository as repo
from servicepulse.case_review import review_temperature
from servicepulse.imports import import_parquet
from servicepulse.measurements import (
    event_window,
    numeric_columns,
    offsets,
    series_window,
    serviceday_summary,
    time_bounds,
    window_comparison,
)
from servicepulse.presentation import (
    category_label,
    fault_label,
    german_number,
    measure_label,
    measurement_figure,
    unit,
)
from servicepulse.research import (
    DEMO_CASES,
    case_observation,
    coverage_rows,
)
from servicepulse.ui.common import chart, table, technical_error


def render_operation(
    df: pd.DataFrame,
    filtered: pd.DataFrame,
    files: pd.DataFrame,
    registered_devices: pd.DataFrame,
    root: Path,
) -> None:
    """Zeigt vorhandene Messdaten und Vergleiche ohne Lückenfüllung."""

    def choose_demo(code):
        selected_device, selected_date, _ = DEMO_CASES[code]
        matching = df[
            df.device_id.eq(selected_device) & df.event_date.eq(pd.Timestamp(selected_date))
        ]
        if matching.empty:
            return
        st.session_state["measurement_device"] = selected_device
        st.session_state[f"service_day_{selected_device}"] = matching.index[0]
        st.session_state[f"measure_{selected_device}"] = "RTD"
        st.session_state["comparison_days"] = 7
        st.session_state["period_mode"] = "Rund um einen Servicetag"
        st.session_state["link_service_filters"] = False
        st.session_state["managed_device"] = selected_device
        st.session_state["device_search"] = ""

    st.subheader("Den Servicetag im Betrieb betrachten")
    st.write(
        "Die Fallanalyse hat eine eigene Geräte-, Service- und Zeitraumwahl. Die Servicefilter links verändern diesen Untersuchungsfall standardmäßig nicht."
    )
    temperatures = files[files.kind.eq("temp")]
    for area, (code, (example_device, example_date, example_label)) in zip(
        st.columns(3), DEMO_CASES.items()
    ):
        available = not df[
            df.device_id.eq(example_device) & df.event_date.eq(pd.Timestamp(example_date))
        ].empty and example_device in set(temperatures.device_id)
        area.button(
            f"Beispiel: {example_label}",
            key=f"demo_{code}",
            on_click=choose_demo,
            args=(code,),
            disabled=not available,
            width="stretch",
            help=f"Gerät {example_device}, {pd.Timestamp(example_date):%d.%m.%Y}, Kammertemperatur und sieben Tage je Vergleichsfenster. Verwendet die gesamte Servicequelle, ohne die Servicefilter links zu ändern.",
        )
    if temperatures.empty:
        st.info(
            "Keine lesbaren Betriebsmessdateien vorhanden. Die Serviceverwaltung bleibt unabhängig davon verfügbar. Messdateien lassen sich nach der Importanleitung ergänzen."
        )
    else:
        options = registered_devices["Geräte-ID"].tolist()
        preferred = "806279" if "806279" in options else options[0]
        device = st.selectbox(
            "1 · Gerät auswählen",
            options,
            index=options.index(preferred),
            key="measurement_device",
            help="Die Geräte-ID bleibt die eindeutige Kennung. Hier sind alle Geräte mit Messdaten verfügbar, auch ohne Serviceeintrag.",
        )
        matches = temperatures[temperatures.device_id.eq(device)]
        if matches.empty:
            st.info(
                "Für dieses Gerät sind keine Temperaturmessdaten vorhanden. Ein neuer Servicebericht erzeugt keine Sensordaten."
            )
        else:
            with st.expander("Expertenansicht · Messdatei und Originalfelder"):
                selected_path = st.selectbox(
                    "Messdatei auswählen",
                    matches.path.tolist(),
                    format_func=lambda p: Path(p).name,
                    key=f"measurement_file_{device}",
                )
                st.code(selected_path, language=None)
                st.caption(
                    "Veröffentlichte Temperaturdaten sind bereits nach Autorenmethode zeitkorrigiert. Originalfelder und Bitcodes bleiben in der Datei erhalten."
                )
                linked = st.checkbox(
                    "Servicefilter links auch auf Fallliste und Markierungen anwenden",
                    value=False,
                    key="link_service_filters",
                )
            path = Path(selected_path)
            numeric = numeric_columns(path)
            case_source = filtered if linked else df
            candidates = case_source[
                case_source.device_id.eq(device) & case_source.event_date.notna()
            ]
            st.caption(
                "Fallliste: aktive Serviceauswahl."
                if linked
                else "Fallliste: alle dokumentierten Serviceeinträge dieses Geräts. Der nachfolgende Messzeitraum ist unabhängig vom Servicezeitraum links."
            )
            mode = st.radio(
                "Untersuchungsart",
                ["Rund um einen Servicetag", "Freier Zeitraum"],
                horizontal=True,
                key="period_mode",
            )
            chosen_date = None
            if mode == "Rund um einen Servicetag" and (not candidates.empty):
                indices = candidates.index.tolist()
                leak_ids = candidates[candidates.category.eq("Refrigerant leakage")].index.tolist()
                row_id = st.selectbox(
                    "2 · Dokumentierten Serviceeintrag auswählen",
                    indices,
                    index=indices.index(leak_ids[0]) if leak_ids else 0,
                    format_func=lambda i: (
                        f"{df.loc[i, 'event_date']:%d.%m.%Y} · {category_label(df.loc[i, 'category'])}"
                    ),
                    key=f"service_day_{device}",
                )
                chosen_date = df.loc[row_id, "event_date"]
                st.caption(
                    f"Dokumentierter Anlass: {(fault_label(df.loc[row_id, 'fault_text']) if df.loc[row_id, 'origin'] == 'research' else df.loc[row_id, 'fault_text'])} · Geräte-ID {device}"
                )
                st.caption(
                    f"Quelle: {df.loc[row_id, 'source_file']} · Bericht {int(df.loc[row_id, 'report_id'])}. "
                    + (
                        f"Original-Excel-Zeile {int(df.loc[row_id, 'source_row'])}."
                        if df.loc[row_id, "origin"] == "research"
                        else "Selbst erfasster Servicebericht."
                    )
                )
                measure = st.selectbox(
                    "3 · Messgröße wählen",
                    numeric,
                    index=numeric.index("RTD") if "RTD" in numeric else 0,
                    format_func=measure_label,
                    key=f"measure_{device}",
                )
                days = st.slider(
                    "Tage vor und nach dem Servicetag", 1, 30, 7, key="comparison_days"
                )
                start, end = (
                    chosen_date - pd.Timedelta(days=days),
                    chosen_date + pd.Timedelta(days=days + 1),
                )
                if device == "806031" and chosen_date == pd.Timestamp("2023-02-03"):
                    st.warning(
                        "Datumswiderspruch: Excel nennt den 03.02.2023, Autorenliste und Auftragsdatum im Bericht den 02.03.2023. Das Excel-Datum wurde nicht automatisch verändert."
                    )
            else:
                if mode == "Rund um einen Servicetag":
                    st.info(
                        "Kein Serviceeintrag für dieses Gerät in der gewählten Fallliste. Du kannst trotzdem einen freien Messzeitraum betrachten."
                    )
                measure = st.selectbox(
                    "3 · Messgröße wählen",
                    numeric,
                    index=numeric.index("RTD") if "RTD" in numeric else 0,
                    format_func=measure_label,
                    key=f"measure_{device}",
                )
                first, last = time_bounds(path)
                last_day = (
                    pd.Timestamp(last).normalize()
                    if last is not None
                    else pd.Timestamp("2023-04-01")
                )
                first_day = (
                    max(pd.Timestamp(first).normalize(), last_day - pd.Timedelta(days=6))
                    if first is not None
                    else last_day
                )
                measurement_dates = st.date_input(
                    "Messzeitraum von – bis",
                    (first_day.date(), last_day.date()),
                    format="DD.MM.YYYY",
                    key=f"measurement_dates_{device}",
                )
                start = pd.Timestamp(measurement_dates[0]) if len(measurement_dates) else first_day
                end = (
                    pd.Timestamp(measurement_dates[-1]) + pd.Timedelta(days=1)
                    if len(measurement_dates)
                    else last_day + pd.Timedelta(days=1)
                )
                if len(measurement_dates) != 2:
                    st.info(
                        "Bitte Anfang und Ende auswählen. Bei einem gewählten Datum wird zunächst dieser einzelne Tag angezeigt."
                    )
            if device == "806018":
                st.warning(
                    "Gerätezuordnung ungeklärt: Eine Rohdatei im Geräteordner 806018 nennt die Kennung 806022. Die Zuordnung der Autoren bleibt erhalten, ist aber fachlich noch zu klären."
                )
            st.caption(
                "RTD ist der Widerstandstemperatursensor in der Kühlkammer. Er misst lokal und beschreibt nicht zwingend die Temperatur an jedem Ort der Kammer."
            )
            bucket = st.selectbox(
                "Werte zusammenfassen pro",
                ["hour", "day", "minute"],
                format_func=lambda value: {"hour": "Stunde", "day": "Tag", "minute": "Minute"}[
                    value
                ],
                key="aggregation",
                help="Jedes Intervall zeigt den Durchschnitt sowie den kleinsten und größten beobachteten Messwert. Es wird nicht über Messlücken interpoliert.",
            )
            st.markdown(f"#### 4 · Messverlauf: {measure_label(measure)} · Gerät {device}")
            st.caption(f"Zeitraum: {start:%d.%m.%Y} bis {end - pd.Timedelta(days=1):%d.%m.%Y}")
            if (end - start).days > 366 and bucket == "minute":
                st.warning(
                    "Bitte für die Minutenansicht höchstens 366 Tage auswählen oder auf Stunden bzw. Tage umstellen."
                )
            else:
                try:
                    curve = series_window(path, measure, start, end, bucket)
                    if curve.empty:
                        st.warning(
                            "Keine Messwerte in diesem Zeitraum. Es werden keine entfernten Messpunkte als Ersatz verwendet."
                        )
                    else:
                        marks = candidates[
                            (candidates.event_date >= start) & (candidates.event_date < end)
                        ]
                        chart(
                            measurement_figure(curve, measure, bucket, marks.event_date.unique()),
                            "measurement_curve",
                        )
                        st.caption(
                            "Mittelwert: Durchschnitt der vorhandenen Messwerte. Minimum und Maximum: kleinster und größter Wert je Intervall. Leere Intervalle bleiben Lücken; die Kurve enthält keine erfundenen Zwischenwerte."
                        )
                        st.download_button(
                            "Messverlauf als CSV herunterladen",
                            curve.to_csv(index=False).encode("utf-8-sig"),
                            "servicepulse_messwerte.csv",
                            "text/csv",
                            key="export_measurements",
                            help="Exportiert die unveränderten berechneten Aggregate und Messpunktzahlen mit technischen Originalbezeichnungen.",
                        )
                    if device == "806279" and measure == "RTD":
                        gaps, daily, warm, states = review_temperature(path, start, end)
                        if not gaps.empty:
                            largest = gaps.iloc[0]
                            st.warning(
                                f"In diesem Fenster liegen zwischen {largest.previous:%d.%m.%Y %H:%M} und {largest.next_time:%d.%m.%Y %H:%M} rund {german_number(largest.seconds / 3600, 2)} Stunden ohne Zwischenmessungen. Die Linie bleibt dort unterbrochen."
                            )
                        if warm.rows:
                            st.write(
                                f"Tatsächlich gemessen: {int(warm.rows)} Werte über +15 °C, von {warm.first_time:%d.%m.%Y %H:%M} bis {warm.last_time:%d.%m.%Y %H:%M}; höchster Wert {german_number(warm.maximum, 2)} °C. Das anschließende Abkühlen ist beobachtbar; eine Ursache ist damit nicht bewiesen."
                            )
                        event_paths = files[files.device_id.eq(device) & files.kind.eq("events")]
                        clock_source = (
                            root / "research/reference/data/raw_data/other_data/time_offsets.csv"
                        )
                        if len(event_paths) == 1 and clock_source.exists():
                            clock_offset = offsets(clock_source).get(device)
                            if clock_offset is not None:
                                power = event_window(
                                    event_paths.iloc[0].path, start, end, clock_offset
                                )
                                power = power[power.Event.isin(["Shutdown", "Display Power On"])]
                                if not power.empty:
                                    labels = {
                                        "Shutdown": "Abschaltung gemeldet",
                                        "Display Power On": "Einschalten der Anzeige gemeldet",
                                    }
                                    st.info(
                                        "Geräteprotokoll: "
                                        + "; ".join(
                                            (
                                                f"{row.Datetime:%d.%m.%Y %H:%M:%S}: {labels[row.Event]}"
                                                for row in power.itertuples()
                                            )
                                        )
                                        + ". Zugeordnet mit der konstanten Autoren-Uhrkorrektur. Das belegt keine Ursache der Lücke und keine Reparaturwirkung."
                                    )
                        with st.expander(
                            "Expertenansicht · Nachprüfung 806279, Lücken und Betriebskennzeichen"
                        ):
                            st.dataframe(daily, hide_index=True, width="stretch")
                            st.dataframe(gaps, hide_index=True, width="stretch")
                            st.dataframe(states, hide_index=True, width="stretch")
                            st.caption(
                                "Die zwei niederwertigsten State-Bits werden entsprechend der Autorenbeschreibung als Verdichtersignale angezeigt. Das ist keine unabhängige Prüfung der Hardware und keine vollständige Dekodierung aller Zustandsbits. Aus Alarmen, Bits oder Lücken wird keine Reparaturwirkung abgeleitet."
                            )
                    st.info(
                        "Die farbige Fläche markiert den dokumentierten Servicetag – keinen nachgewiesenen Fehlerbeginn. Ein Unterschied vor und nach diesem Tag beweist keine Reparaturwirkung."
                    )
                    if chosen_date is not None:
                        comparison = window_comparison(path, measure, chosen_date, days)
                        day = serviceday_summary(path, measure, chosen_date)
                        st.subheader("5 · Vor und nach dem Servicetag")
                        st.caption(
                            f"Jeweils {days} Tage; der Servicetag selbst ist aus beiden Vergleichsfenstern ausgeschlossen. Der Durchschnitt gewichtet jeden vorhandenen Messwert gleich."
                        )
                        for area, (_, row) in zip(st.columns(2), comparison.iterrows()):
                            with area:
                                label = (
                                    "Vor dem Servicetag"
                                    if row["window"] == "Vorher"
                                    else "Nach dem Servicetag"
                                )
                                st.metric(
                                    label,
                                    f"{german_number(row['mean'], 2)} {unit(measure)}"
                                    if pd.notna(row["mean"])
                                    else "Keine Messwerte",
                                    help="Durchschnitt der vorhandenen Messwerte im jeweiligen Fenster.",
                                )
                                st.caption(
                                    f"Gültige Messpunkte: {german_number(row['valid'])} · Median: {german_number(row['median'], 2)} {unit(measure)}"
                                )
                                st.caption(
                                    f"Minimum: {german_number(row['minimum'], 2)} {unit(measure)} · Maximum: {german_number(row['maximum'], 2)} {unit(measure)}"
                                )
                        st.caption(
                            f"Am Servicetag selbst: {german_number(day.valid)} gültige Messpunkte. Diese gehen nicht in die beiden Vergleichsmittelwerte ein."
                        )
                        if (comparison.valid == 0).any():
                            st.warning(
                                "Mindestens ein Vergleichsfenster enthält keine gültigen Messwerte. Ein Vorher-Nachher-Vergleich ist für dieses Fenster nicht möglich."
                            )
                        st.caption(
                            "Unterschiedliche Messpunktzahlen und Lücken können die Vergleichbarkeit begrenzen. Auch viele Messpunkte belegen keine kontinuierliche Aufzeichnung."
                        )
                        st.subheader("6 · Beobachtung und Datenlücken verstehen")
                        st.write(case_observation(comparison, day, unit(measure)))
                        st.dataframe(
                            coverage_rows(comparison, day, days),
                            hide_index=True,
                            width="stretch",
                            key="case_coverage",
                        )
                        st.caption(
                            "Eine Stunde gilt hier als beobachtet, sobald mindestens ein gültiger Messwert vorliegt. Das ist keine vollständige Stundenabdeckung. Doppelte Zeitstempel erhöhen nicht die Anzahl beobachteter Stunden."
                        )
                        st.info(
                            "Noch zu prüfen: Betriebszustände, Türöffnungen, Abtauen, zeitlicher Beginn des Defekts und Inhalt der Serviceberichte. Ohne diese Prüfungen lässt sich eine Veränderung nicht einer Reparatur zuschreiben."
                        )
                        with st.expander("Expertenansicht · Vergleichsfenster und Messpunktzahlen"):
                            table(comparison)
                            st.caption(
                                "Median: mittlerer Wert der sortierten Messwerte. Die Grenzen zeigen den ersten und letzten vorhandenen Messpunkt, keine garantierte lückenlose Abdeckung."
                            )
                    event_files = files[files.device_id.eq(device) & files.kind.eq("events")]
                    offpath = root / "research/reference/data/raw_data/other_data/time_offsets.csv"
                    with st.expander("Expertenansicht · Geräteereignisse und Uhrkorrektur"):
                        st.caption(
                            "Gerätemeldungen wie Türöffnungen sind keine zusätzlichen Serviceeinträge. Bis zu 1.000 Originalmeldungen; diese werden zur Nachprüfbarkeit nicht automatisch übersetzt."
                        )
                        if len(event_files) > 1:
                            st.warning(
                                "Mehrere Meldungsdateien für dieselbe Geräte-ID. Die Zuordnung muss zuerst geklärt werden."
                            )
                        elif not event_files.empty and offpath.exists():
                            clock = offsets(offpath)
                            if device in clock:
                                st.caption(
                                    f"Konstante Uhrkorrektur der Autoren: {clock[device]}. Historische Uhrdrift ist damit nicht geprüft."
                                )
                                table(
                                    event_window(
                                        event_files.iloc[0].path, start, end, clock[device]
                                    ),
                                    height=250,
                                )
                            else:
                                st.warning(
                                    "Keine Uhrkorrektur für dieses Gerät vorhanden; Meldungen werden nicht zeitlich zugeordnet."
                                )
                        else:
                            st.info(
                                "Keine eindeutig zuordenbaren Meldungsdaten mit Uhrenreferenz vorhanden."
                            )
                except Exception as exc:
                    st.error(
                        "Die Messdaten konnten für diese Auswahl nicht ausgewertet werden. Bitte eine andere Messgröße oder einen anderen Zeitraum wählen und die Datenqualität prüfen."
                    )
                    technical_error(exc)
    with st.expander("Erweiterte Funktion · Weitere Messdateien importieren"):
        st.write(
            f"Es sind bereits **{len(files)} veröffentlichte bzw. lokal ergänzte Messdateien** verfügbar. Im geprüften Forschungsbestand sind es 106. Für die normale Nutzung ist kein erneuter Import nötig."
        )
        st.caption(
            "Parquet ist das Dateiformat der Betriebsmessdaten. Nur zum Ergänzen weiterer Dateien verwenden. Vorhandene Dateien werden nicht überschrieben."
        )
        st.markdown(
            "Dateiname beispielsweise `806279_temp.parquet` für Messwerte oder `806279_events.parquet` für Meldungen. Herkunft und Lizenz zusätzlicher Dateien separat dokumentieren. Temperaturdateien müssen bereits zeitkorrigiert sein, Meldungsdateien die interne Gerätezeit der Autorenpipeline verwenden."
        )
        upload_source = st.text_input(
            "Herkunft und Nutzungsrecht der Messdatei",
            key="measurement_source",
            help="Bitte Quelle und Berechtigung zur Nutzung dokumentieren.",
        )
        upload = st.file_uploader(
            "Messdatei auswählen (Parquet, höchstens 300 MB)", type="parquet", key="parquet_upload"
        )
        if upload is not None and st.button("Datei prüfen und importieren", key="import_parquet"):
            try:
                destination, digest = import_parquet(
                    upload.getvalue(),
                    upload.name,
                    root / "data/raw/imported",
                    registry=repo.file_digests(),
                    source=upload_source,
                )
                try:
                    repo.register_file(destination, upload_source)
                except Exception:
                    destination.unlink()
                    raise
                st.session_state["import_success"] = destination.name
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(
                    "Die Datei konnte nicht gespeichert werden. Bitte Speicherplatz und Schreibrechte prüfen."
                )
                technical_error(exc)
        if "import_success" in st.session_state:
            st.success(
                f"Datei erfolgreich geprüft und übernommen: {st.session_state.pop('import_success')}"
            )
        st.caption(
            "Größere Dateien nach der lokalen Importanleitung in docs/datenimport.md direkt nach data/raw/<Modell>/ kopieren. Danach den Qualitätsbericht neu erstellen."
        )
