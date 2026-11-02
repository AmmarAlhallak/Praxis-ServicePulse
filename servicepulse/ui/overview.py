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
    st.caption(
        f"{df.loc[df.device_valid, 'device_id'].nunique()} von {len(registered_devices)} registrierten Geräten haben insgesamt {len(df)} dokumentierte Serviceeinträge. Geräte ohne Eintrag sind nicht automatisch störungsfrei."
    )
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Welche Fehlerkategorien kommen am häufigsten vor?")
        grouped = st.toggle(
            "Kategorien mit und ohne Behebung zusammenfassen",
            value=True,
            key="group_categories",
            help="Ändert nur dieses Diagramm. Originalkategorien und Kennzahlen bleiben unverändert.",
        )
        column = "category_group" if grouped else "category"
        show_counts(filtered, column, "Fehlerkategorie", "fault_categories")
        if not filtered.empty:
            top = filtered[column].value_counts()
            st.caption(
                f"{category_label(top.index[0])}: {int(top.iloc[0])} Einträge in dieser Auswahl."
            )
        st.caption(
            "Die Häufigkeiten beschreiben Serviceeinträge und belegen keine unabhängigen Ausfälle oder Ausfallwahrscheinlichkeiten."
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
            "Die Beobachtungszeiten unterscheiden sich. Einträge pro Gerät sind keine Ausfallraten."
        )

    st.subheader("Welche Geräte haben wiederholte Einträge derselben Kategorie?")
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

    with st.expander("Alle Serviceberichte und Herkunft"):
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
        st.caption(
            "Originalwerte und Herkunft; die Originalkategorien bleiben auch im CSV erhalten."
        )
        st.dataframe(filtered, hide_index=True, width="stretch", height=300)

    with st.expander("Zeitliche Verteilung der Serviceeinträge"):
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
