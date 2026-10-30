"""Zeigt die bisherigen deskriptiven Serviceauswertungen unverändert."""

import pandas as pd
import plotly.express as px
import streamlit as st

from servicepulse.presentation import category_label, faults_export, style_figure
from servicepulse.ui.common import chart, show_counts, table


def render_overview(
    df: pd.DataFrame, filtered: pd.DataFrame, registered_devices: pd.DataFrame
) -> None:
    """Zeigt die bisherigen deskriptiven Serviceauswertungen unverändert."""
    st.metric(
        "Registrierte Geräte",
        len(registered_devices),
        help="Alle registrierten Geräte, auch ohne dokumentierten Service. Geräte ohne Bericht sind nicht automatisch störungsfrei.",
    )
    st.caption(
        "Die Kennzahlen werden bei jeder Aktualisierung aus den in PostgreSQL gespeicherten Berichten berechnet. Forschungsdaten und selbst erfasste Berichte sind in der Historie gekennzeichnet."
    )
    st.subheader("Welche Serviceanlässe sind dokumentiert?")
    left, right = st.columns([3, 2], gap="large")
    with left:
        show_counts(filtered, "category_group", "Fehlerkategorie", "overview_categories")
        st.caption(
            "Für diesen Überblick ist „ohne Behebung“ zur zugehörigen Hauptkategorie zusammengefasst. Alle Einträge bleiben enthalten."
        )
    with right:
        st.markdown("#### Die Auswahl einordnen")
        if not filtered.empty:
            top = filtered.category_group.value_counts()
            st.write(
                f"**{category_label(top.index[0])}** ist mit **{int(top.iloc[0])} Einträgen** die häufigste Gruppe in der aktuellen Auswahl."
            )
        st.info(
            "Ein Serviceeintrag ist kein nachgewiesener unabhängiger Ausfall. Aus diesen Häufigkeiten ergibt sich keine Ausfallwahrscheinlichkeit."
        )
        st.markdown(
            "**So gehst du vor**\n\n1. Serviceauswahl links eingrenzen.\n2. Häufigkeiten unter „Übersicht“ vergleichen.\n3. Unter „Betriebsanalyse & Vergleiche“ einen Servicetag im Messverlauf ansehen."
        )
    st.subheader("Serviceeinträge der aktuellen Auswahl")
    from servicepulse.management import report_table

    report_table(filtered)
    st.download_button(
        "Serviceauswahl als CSV herunterladen",
        faults_export(filtered),
        "servicepulse_serviceeintraege.csv",
        "text/csv",
        key="export_faults",
        help="Enthält deutsche Lesehilfen und alle Originalspalten, Originalwerte und Quellzeilen zur Nachprüfung.",
    )
    with st.expander("Originalwerte und Herkunft der ausgewählten Einträge"):
        st.caption(
            "Unveränderte Originalwerte und technische Zusatzfelder. Die Originalkategorien sind auch im CSV-Export enthalten."
        )
        st.dataframe(filtered, hide_index=True, width="stretch", height=300)
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Fehlerkategorien vergleichen")
        grouped = st.toggle(
            "Einträge ohne Behebung mit der Hauptkategorie zusammenfassen",
            value=False,
            key="group_categories",
            help="Ändert nur dieses Diagramm. Originalkategorien und Kennzahlen bleiben unverändert.",
        )
        show_counts(
            filtered,
            "category_group" if grouped else "category",
            "Fehlerkategorie",
            "fault_categories",
        )
        st.caption(
            "Dargestellt sind dokumentierte Serviceeinträge nach Autorenkategorie. Häufigere Meldungen belegen weder eine höhere Ausfallwahrscheinlichkeit noch unabhängige Defekte. Die Abgrenzung einzelner Serviceepisoden bleibt offen."
        )
    with right:
        st.subheader("Einträge nach Geräten")
        show_counts(filtered, "device_id", "Geräte-ID", "device_counts")
        if not filtered.empty:
            counts = filtered.device_id.value_counts()
            st.write(
                f"Beispiel aus der Auswahl: Gerät {counts.index[0]} hat {int(counts.iloc[0])} dokumentierte Einträge."
            )
        st.caption(
            "Die Beobachtungsdauern und Messlücken unterscheiden sich je Gerät. Diese Rohhäufigkeiten sind keine Ausfallraten und kein fairer Zuverlässigkeitsrang. Vergleichbare Betriebszeiten und Serviceepisoden müssen dafür erst definiert werden."
        )
    st.subheader("Mehrere Einträge derselben Kategorie")
    repeated = (
        filtered.groupby(["device_id", "category"]).size().reset_index(name="Serviceeinträge")
    )
    repeated = repeated[repeated.Serviceeinträge > 1]
    if repeated.empty:
        st.caption(
            "In dieser Auswahl gibt es keine mehrfach dokumentierte Kombination aus Gerät und Originalkategorie."
        )
    table(repeated, key="repeated_rows")
    st.caption(
        "Die Tabelle zählt Kombinationen, keine unabhängigen Ausfälle. Eine ungelöste Störung kann mehrere Serviceeinträge verursachen."
    )
    st.subheader("Wann wurde Service registriert?")
    timeline = (
        filtered.dropna(subset=["event_date"])
        .assign(Monat=lambda x: x.event_date.dt.to_period("M").dt.to_timestamp())
        .groupby("Monat")
        .size()
        .reset_index(name="Serviceeinträge")
    )
    if len(timeline):
        figure = px.bar(
            timeline, x="Monat", y="Serviceeinträge", color_discrete_sequence=["#147d92"]
        )
        figure.update_traces(hovertemplate="%{x|%m.%Y}<br>Serviceeinträge: %{y}<extra></extra>")
        figure.update_xaxes(tickformat="%m.%Y")
        chart(style_figure(figure, 300), "service_timeline")
        peak = timeline.loc[timeline.Serviceeinträge.idxmax()]
        st.write(
            f"Ein Monat mit der höchsten Eintragszahl in dieser Auswahl ist {peak['Monat']:%m.%Y} mit {int(peak.Serviceeinträge)} Einträgen. Daraus folgt kein saisonales Ausfallmuster; Beobachtungsumfang und Berichtspraxis können sich unterscheiden."
        )
    st.caption(
        "Registrierungsdaten haben Tagesauflösung. Ein Registrierungsdatum beschreibt nicht den nachgewiesenen Beginn eines Defekts."
    )
