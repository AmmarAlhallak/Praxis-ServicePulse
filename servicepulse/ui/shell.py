"""Zeigt Servicefilter und Kennzahlen; gibt die ausgewählten Berichte zurück."""

import pandas as pd
import streamlit as st

from servicepulse.faults import metrics
from servicepulse.presentation import category_label
from servicepulse.research import apply_service_selection


def render_service_filters(df: pd.DataFrame, files: pd.DataFrame) -> pd.DataFrame:
    """Zeigt Servicefilter und Kennzahlen; gibt die ausgewählten Berichte zurück."""
    if st.session_state.get("service_filter_version") != 2:
        for old_key in [
            "devices",
            "categories",
            "date_range",
            "all_devices",
            "all_categories",
            "limit_service_dates",
            "service_start",
            "service_end",
        ]:
            st.session_state.pop(old_key, None)
        st.session_state["service_filter_version"] = 2
    with st.sidebar:
        st.markdown("### ❄ ServicePulse")
        st.caption("Lokale Geräte- und Serviceverwaltung")
        st.subheader("Serviceauswahl")
        st.caption(
            "Diese Filter gelten für Übersicht und Serviceexport. Geräteverwaltung und Betriebsanalyse haben eine eigene Geräte- und Fallauswahl."
        )
        if st.button("Alle Filter zurücksetzen", width="stretch"):
            for key in [
                "devices",
                "categories",
                "date_range",
                "include_undated",
                "all_devices",
                "all_categories",
                "limit_service_dates",
                "service_start",
                "service_end",
            ]:
                st.session_state.pop(key, None)
            st.rerun()
        with st.expander("Geräte auswählen"):
            device_options = sorted(df.device_id.dropna().unique())
            all_devices = st.checkbox("Alle Geräte berücksichtigen", value=True, key="all_devices")
            device_selection = st.multiselect(
                "Geräte-ID suchen",
                device_options,
                default=[],
                key="devices",
                disabled=all_devices,
                placeholder="Geräte-ID eingeben oder auswählen",
                help="Für einzelne Geräte das Häkchen bei „Alle Geräte“ entfernen. Die Auswahl ist durchsuchbar. Eine dann leere Auswahl zeigt keine Einträge.",
            )
            devices = None if all_devices else device_selection
        with st.expander("Fehlerkategorien auswählen"):
            category_options = sorted(df.category.unique(), key=category_label)
            all_categories = st.checkbox(
                "Alle Kategorien berücksichtigen", value=True, key="all_categories"
            )
            category_selection = st.multiselect(
                "Fehlerkategorie suchen",
                category_options,
                default=[],
                format_func=category_label,
                key="categories",
                disabled=all_categories,
                placeholder="Kategorie eingeben oder auswählen",
                help="Die deutschen Namen sind Anzeigeübersetzungen. Originalkategorien bleiben unverändert erhalten.",
            )
            categories = None if all_categories else category_selection
        dates = df.event_date.dropna()
        limit_dates = st.checkbox(
            "Servicezeitraum eingrenzen", value=False, key="limit_service_dates"
        )
        start_date = st.date_input(
            "Servicedatum ab",
            dates.min().date() if len(dates) else None,
            format="DD.MM.YYYY",
            key="service_start",
            disabled=not limit_dates,
        )
        end_date = st.date_input(
            "Servicedatum bis",
            dates.max().date() if len(dates) else None,
            format="DD.MM.YYYY",
            key="service_end",
            disabled=not limit_dates,
        )
        include_undated = st.checkbox(
            "Einträge ohne gültiges Datum einbeziehen", value=True, key="include_undated"
        )
        st.divider()
        st.caption(
            f"{len(df)} Serviceeinträge · {df.loc[df.device_valid, 'device_id'].nunique()} betroffene Geräte\n\n{len(files)} verfügbare Messdateien"
        )
        with st.expander("Begriffe kurz erklärt"):
            st.markdown(
                "**Serviceeintrag:** eine dokumentierte Meldung oder Maßnahme aus der Serviceübersicht, kein automatisch bestätigter Ausfall.\n\n**Fehlerkategorie:** die von den Forschern zugeordnete Gruppe eines Eintrags.\n\n**Ohne Behebung:** Originalzusatz „No fix“; der Bericht dokumentiert keine Behebung. Weitere Einträge können denselben Zustand betreffen.\n\n**Messdaten fehlen:** Originalkategorie „Data missing“; keine leere Excel-Zelle.\n\n**Messabdeckung:** zeigt, ob und wie viele Messpunkte in einem Zeitfenster vorliegen. Einzelne Punkte belegen keine lückenlose Aufzeichnung."
            )
    filtered, filter_problem = apply_service_selection(
        df, devices, categories, limit_dates, start_date, end_date, include_undated
    )
    if filter_problem:
        st.warning(filter_problem)
    device_summary = (
        f"alle {len(device_options)}" if all_devices else ", ".join(devices) if devices else "keine"
    )
    category_summary = (
        f"alle {len(category_options)}"
        if all_categories
        else ", ".join(map(category_label, categories))
        if categories
        else "keine"
    )
    period_summary = (
        "gesamter dokumentierter Zeitraum"
        if not limit_dates
        else f"{start_date:%d.%m.%Y} – {end_date:%d.%m.%Y}"
        if start_date and end_date and (not filter_problem)
        else "ungültig / unvollständig"
    )
    active_summary = f"Aktive Servicefilter · Geräte: {device_summary} · Kategorien: {category_summary} · Zeitraum: {period_summary} · Einträge ohne Datum: {('einbezogen' if include_undated else 'ausgeschlossen')}"
    with st.sidebar:
        st.info(active_summary)
    m = metrics(filtered)
    metric_items = [
        (
            "Serviceeinträge",
            m["entries"],
            "Dokumentierte Einträge in der aktuellen Auswahl. Ein Eintrag kann mehrere Komponenten betreffen.",
        ),
        (
            "Betroffene Geräte",
            m["devices"],
            "Unterschiedliche gültige Geräte-IDs mit mindestens einem ausgewählten Eintrag.",
        ),
        (
            "Mehrfach dokumentierte Geräte",
            m["devices_multiple_entries"],
            "Geräte mit mehr als einem Eintrag. Das beweist keine wiederholten unabhängigen Ausfälle.",
        ),
        (
            "Wiederholte Gerät/Kategorie-Paare",
            m["repeated_device_category_pairs"],
            "Anzahl der Geräte- und Originalkategorie-Kombinationen mit mehreren Einträgen. „Ohne Behebung“ bleibt eigenständig.",
        ),
    ]
    for column, (label, value, help_text) in zip(st.columns(4), metric_items):
        column.metric(label, value, help=help_text)
    st.caption(
        f"Aktuelle Serviceauswahl: {len(filtered)} von {len(df)} Einträgen. Mehrere Einträge können denselben ungelösten Zustand beschreiben."
    )
    st.caption(active_summary)
    return filtered


def configure_page() -> None:
    """Setzt die bisherigen Seiteneinstellungen und Farben."""
    st.set_page_config(
        page_title="ServicePulse · Kälteanlagen verstehen", page_icon="❄", layout="wide"
    )
    st.markdown(
        '<style>\n.stApp {background:#f3f7fa;color:#183447;}\n.block-container {max-width:1440px;padding-top:4.5rem;padding-bottom:3rem;}\nh1,h2,h3 {color:#16364a;letter-spacing:-.025em;} h1{font-size:2.35rem !important;}\n[data-testid="stSidebar"] {background:#eaf1f5;border-right:1px solid #d9e5ec;}\n[data-testid="stMetric"] {background:#fff;border:1px solid #dce7ed;border-radius:14px;padding:16px;}\n[data-testid="stMetricValue"] {color:#126e80;}\n[data-testid="stMetricLabel"] p {white-space:normal !important;overflow:visible !important;text-overflow:clip !important;}\n[data-testid="stMetricLabel"] {min-height:4rem;}\n[data-testid="stTabs"] [role="tablist"] {gap:10px;border-bottom:1px solid #d8e4eb;}\n[data-testid="stTabs"] [role="tab"] {padding:14px 8px;font-weight:600;white-space:nowrap;}\n[data-testid="stExpander"] {background:#fff;border-radius:12px;}\n[data-testid="stElementToolbar"], [data-testid="stToolbarActions"] {display:none;}\n[data-testid="stFileUploaderDropzoneInstructions"] {display:none;}\n[data-testid="stFileUploaderDropzone"] button {font-size:0;}\n[data-testid="stFileUploaderDropzone"] button::after {content:\'Datei auswählen\';font-size:14px;}\n@media(max-width:800px){h1{font-size:1.8rem !important;}.block-container{padding-left:1rem;padding-right:1rem;}}\n</style>',
        unsafe_allow_html=True,
    )
