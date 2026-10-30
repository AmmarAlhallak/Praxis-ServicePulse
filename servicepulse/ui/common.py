"""Gemeinsame Darstellung; verändert keine fachlichen Daten."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from servicepulse.presentation import counts_figure, display_frame

CHART_CONFIG = {"displayModeBar": False, "responsive": True, "displaylogo": False}


def table(frame: pd.DataFrame, key: str | None = None, height: str | int = "auto") -> None:
    """Zeigt eine deutsche Tabellenkopie mit optionaler Widgetkennung und Höhe."""
    st.dataframe(display_frame(frame), hide_index=True, width="stretch", height=height, key=key)


def chart(figure: go.Figure, key: str) -> None:
    """Zeigt die bestehende Plotly-Figur unter einer eindeutigen Widgetkennung."""
    st.plotly_chart(figure, width="stretch", key=key, config=CHART_CONFIG)


def show_counts(frame: pd.DataFrame, column: str, label: str, key: str) -> None:
    """Zeigt eine Servicezählung oder einen Hinweis zur leeren Auswahl."""
    if frame.empty:
        st.info("Für diese Auswahl liegen keine Serviceeinträge vor.")
    else:
        chart(counts_figure(frame, column, label), key)


def technical_error(exc: Exception) -> None:
    """Zeigt den Fehlertyp, ohne SQL-Parameter oder Zugangsdaten offenzulegen."""
    with st.expander("Technische Fehlerdetails"):
        st.code(type(exc).__name__, language=None)


def database_problem(exc: Exception) -> None:
    """Zeigt einen verständlichen Verbindungsfehler ohne Excel-Ersatzbestand."""
    st.error(
        "Die Service-Datenbank ist nicht erreichbar. Bitte das Programm über start.cmd oder F5 starten. Es werden keine veralteten Excel-Daten als aktueller Stand angezeigt."
    )
    technical_error(exc)
