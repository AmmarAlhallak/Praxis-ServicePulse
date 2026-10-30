"""Deutsche Darstellung auf Kopien; keine Änderung von Quellen oder Kennzahlen."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

CATEGORIES = {
    "Refrigerant leakage": "Kältemittelleckage",
    "2nd stage compressor": "Verdichter der 2. Stufe",
    "Electrical malfunction": "Elektrische Störung",
    "Unstable operation": "Instabiler Betrieb",
    "Unstable operation (No fix)": "Instabiler Betrieb (ohne Behebung)",
    "Data missing": "Messdaten fehlen",
    "1st stage compressor": "Verdichter der 1. Stufe",
    "1st stage compressor (No fix)": "Verdichter der 1. Stufe (ohne Behebung)",
    "High condensation": "Hohe Kondensation",
    "High condensation (No fix)": "Hohe Kondensation (ohne Behebung)",
    "Bad insulation": "Mangelhafte Isolierung",
    "Door tightness": "Türdichtheit",
    "Wrong setpoint": "Falscher Sollwert",
    "Unbekannt": "Nicht angegeben",
}
FAULTS = {
    "compressor_stage_2 malfunctional": "Funktionsstörung am Verdichter der 2. Stufe",
    "High condensation water": "Hohe Kondensation (Wasser)",
    "Refrigerant leakage at stage 1": "Kältemittelleckage in der 1. Stufe",
    "Refrigerant leakage at stage 2": "Kältemittelleckage in der 2. Stufe",
    "Refrigerant leakage at stage 1 and 2": "Kältemittelleckage in beiden Stufen",
    "warm_alarm": "Temperaturalarm",
    "warm_interstage": "Erhöhte Zwischenstufentemperatur",
    "electric_wiring": "Elektrische Verdrahtung",
    "main_board": "Hauptplatine",
    "OS_update": "Aktualisierung der Gerätesoftware",
    "compressor_stage_2": "Verdichter der 2. Stufe",
    "setpoint_change": "Änderung des Sollwerts",
    "compressor_stage_2 piston sticking": "Klemmender Kolben am Verdichter der 2. Stufe",
    "Bad insulation": "Mangelhafte Isolierung",
    "Water valve adjustment": "Einstellung des Wasserventils",
    "logic_wiring": "Steuerungsverdrahtung",
    "filter_drier": "Filtertrockner",
    "battery": "Batterie",
    "handle_tightening": "Nachziehen des Türgriffs",
    "relay": "Relais",
    "compressor_stage_1 malfunctional": "Funktionsstörung am Verdichter der 1. Stufe",
    "door_adjustment": "Türeinstellung",
    "instability": "Instabiler Betrieb",
    "fuse_blown": "Ausgelöste Sicherung",
    "display": "Anzeige",
}
MEASURES = {
    "RTD": "Kammertemperatur (RTD)",
    "1st Suc.": "Ansaugtemperatur · 1. Stufe",
    "1st Disc.": "Austrittstemperatur · Verdichter der 1. Stufe",
    "2nd Disc.": "Austrittstemperatur · Verdichter der 2. Stufe",
    "Cond. Air In": "Lufteintritt am Kondensator",
    "Evap. In": "Eintrittstemperatur am Verdampfer",
    "Evap. Out": "Austrittstemperatur am Verdampfer",
    "2nd Evap. In": "Eintrittstemperatur am Verdampfer · 2. Stufe",
    "2nd Evap. Out": "Austrittstemperatur am Verdampfer · 2. Stufe",
    "2nd Suc.": "Ansaugtemperatur · 2. Stufe",
    "Chil. water In": "Eintrittstemperatur des Kühlwassers",
    "2nd Sump": "Ölsumpftemperatur · 2. Stufe",
    "H.E.": "Temperatur am Zwischenwärmetauscher",
    "SetPoint": "Temperatursollwert",
    "Mains Voltage": "Netzspannung",
    "Ambient": "Umgebungstemperatur",
}
COLUMNS = {
    "device_id": "Geräte-ID",
    "event_date": "Servicedatum",
    "fault_text": "Dokumentierter Anlass",
    "category": "Fehlerkategorie",
    "category_group": "Fehlerkategorie",
    "source_row": "Excel-Zeile",
    "day_rows": "Messpunkte am Servicetag",
    "before_rows": "Messpunkte vor dem Servicetag",
    "after_rows": "Messpunkte nach dem Servicetag",
    "before_mean": "Durchschnitt vorher (°C)",
    "after_mean": "Durchschnitt nachher (°C)",
    "date": "Servicedatum",
    "first_time": "Erster Messzeitpunkt",
    "last_time": "Letzter Messzeitpunkt",
    "null_times": "Fehlende Zeitwerte",
    "repeated_timestamps": "Wiederholte Zeitstempel",
    "missing_rtd": "Fehlende Kammertemperaturen",
    "max_gap_seconds": "Größte Messlücke (Sekunden)",
    "median_gap_seconds": "Typischer Messabstand (Sekunden)",
    "gaps_over_day": "Messlücken über einen Tag",
    "min_rtd": "Niedrigste Kammertemperatur (°C)",
    "max_rtd": "Höchste Kammertemperatur (°C)",
    "rows": "Messpunkte",
    "valid": "Gültige Messwerte",
    "mean": "Durchschnitt",
    "median": "Median",
    "minimum": "Minimum",
    "maximum": "Maximum",
    "time": "Zeitpunkt",
    "n": "Gültige Messwerte",
    "window": "Zeitraum",
    "model": "Gerätemodell",
    "kind": "Dateiinhalt",
    "columns": "Originalspalten",
    "observed_hours": "Stunden mit gültigen Messpunkten",
    "path": "Dateipfad",
    "category_raw": "Originalkategorie",
    "reported_count": "Anzahl im Kontrollblatt",
    "calculated_count": "Selbst berechnete Anzahl",
    "matches": "Übereinstimmung",
    "reference_date": "Servicedatum der Autoren",
    "reference_fault": "Beschreibung der Autoren",
    "reference_status": "Quellenvergleich",
    "Datetime": "Zeitpunkt",
    "Datetime_internal": "Interne Gerätezeit",
    "Event": "Originalmeldung",
    "Type": "Meldungscode",
    "Description": "Originalbeschreibung",
    "error": "Fehlerhinweis",
}
STATUS = {
    "Übereinstimmung": "Übereinstimmung",
    "Kein ID/Tag-Treffer": "Kein passender Eintrag am selben Tag",
    "Abweichender Fehlertext": "Unterschiedliche Beschreibung",
}


def category_label(value: object) -> str:
    """Liefert die deutsche Lesehilfe für einen unveränderten Kategoriecode."""
    return CATEGORIES.get(str(value).strip(), "Weitere Kategorie")


def fault_label(value: object) -> str:
    """Liefert die deutsche Lesehilfe für einen dokumentierten Originaltext."""
    return FAULTS.get(str(value).strip(), "Weitere dokumentierte Beschreibung")


def unit(column: str) -> str:
    """Liefert die bekannte Einheit einer Messgröße oder einen ausdrücklichen Hinweis."""
    if column == "Mains Voltage":
        return "V"
    return "°C" if column in MEASURES else "Einheit nicht angegeben"


def measure_label(column: str) -> str:
    """Verbindet die deutsche Messgrößenbezeichnung mit ihrer Einheit."""
    return f"{MEASURES.get(column, 'Weitere Messgröße')} ({unit(column)})"


def german_number(value: float | int, digits: int = 0) -> str:
    """Formatiert eine Zahl deutsch; fehlende Zahlen bleiben ausdrücklich nicht verfügbar."""
    if pd.isna(value):
        return "Nicht verfügbar"
    return f"{value:,.{digits}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Erstellt eine deutsche Ansicht als Kopie; verändert keine Quelldaten."""
    result = frame.copy()
    for column in result.columns:
        if column in {"category", "category_group", "category_raw"}:
            result[column] = result[column].map(category_label)
        elif column in {"fault_text", "reference_fault"}:
            result[column] = result[column].map(
                lambda v: fault_label(v) if pd.notna(v) else "Kein Treffer"
            )
        elif column == "reference_status":
            result[column] = result[column].map(STATUS).fillna("Nicht zugeordnet")
        elif column in {"event_date", "reference_date", "date"}:
            result[column] = (
                pd.to_datetime(result[column], errors="coerce")
                .dt.strftime("%d.%m.%Y")
                .fillna("Nicht angegeben")
            )
        elif column in {"first_time", "last_time", "Datetime", "Datetime_internal"}:
            result[column] = (
                pd.to_datetime(result[column], errors="coerce")
                .dt.strftime("%d.%m.%Y %H:%M")
                .fillna("Keine Messpunkte")
            )
        elif column == "kind":
            result[column] = result[column].map(
                {"temp": "Betriebsmesswerte", "events": "Gerätemeldungen"}
            )
        elif pd.api.types.is_bool_dtype(result[column]):
            result[column] = result[column].map({True: "Ja", False: "Nein"})
    return result.rename(columns=COLUMNS)


def faults_export(frame: pd.DataFrame) -> bytes:
    """Deutsche Lesehilfe zusätzlich zu sämtlichen unveränderten Originalfeldern."""
    export = frame.copy()
    export.insert(0, "Fehlerkategorie (Deutsch)", frame.category.map(category_label))
    export.insert(1, "Beschreibung (Deutsch)", frame.fault_text.map(fault_label))
    return export.to_csv(index=False).encode("utf-8-sig")


def style_figure(figure: go.Figure, height: int = 360) -> go.Figure:
    """Wendet das vorhandene gemeinsame Diagrammlayout an und gibt die Figur zurück."""
    figure.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=18, t=24, b=20),
        font=dict(family="Arial, sans-serif", size=13, color="#243b50"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=",.",
        legend_title_text="",
        legend=dict(orientation="h", y=1.12, x=0),
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#e5edf2", zeroline=False)
    return figure


def counts_figure(frame: pd.DataFrame, column: str, label: str) -> go.Figure:
    """Erstellt ein Balkendiagramm dokumentierter Serviceeinträge."""
    counts = (
        frame[column].value_counts().rename_axis("original").reset_index(name="Serviceeinträge")
    )
    counts[label] = (
        counts.original.map(category_label) if column != "device_id" else counts.original
    )
    figure = px.bar(
        counts, x="Serviceeinträge", y=label, orientation="h", color_discrete_sequence=["#147d92"]
    )
    figure.update_layout(yaxis={"categoryorder": "total ascending"})
    figure.update_traces(hovertemplate="%{y}<br>Serviceeinträge: %{x}<extra></extra>")
    return style_figure(figure, height=max(300, min(620, 45 * len(counts) + 60)))


def measurement_figure(
    curve: pd.DataFrame, column: str, bucket: str, service_days: Iterable[pd.Timestamp]
) -> go.Figure:
    """Zeichnet aggregierte Messwerte; fehlende Zeitraster bleiben sichtbare Linienunterbrechungen."""
    frequency = {"minute": "min", "hour": "h", "day": "D"}[bucket]
    regular = curve.set_index("time").asfreq(frequency).reset_index()
    display = regular.rename(
        columns={"mean": "Mittelwert", "minimum": "Minimum", "maximum": "Maximum"}
    )
    figure = px.line(
        display,
        x="time",
        y=["Minimum", "Maximum", "Mittelwert"],
        labels={"time": "Datum und Uhrzeit", "value": measure_label(column), "variable": ""},
        color_discrete_map={"Mittelwert": "#147d92", "Minimum": "#94bac5", "Maximum": "#da9a55"},
    )
    figure.update_traces(
        connectgaps=False,
        hovertemplate="%{x|%d.%m.%Y %H:%M}<br>%{y:.2f} "
        + unit(column)
        + "<extra>%{fullData.name}</extra>",
    )
    for day in service_days:
        figure.add_vrect(
            x0=pd.Timestamp(day),
            x1=pd.Timestamp(day) + pd.Timedelta(days=1),
            fillcolor="#eaa67c",
            opacity=0.22,
            line_width=0,
        )
    style_figure(figure, 420)
    figure.update_xaxes(tickformat="%d.%m.%Y", hoverformat="%d.%m.%Y %H:%M")
    return figure
