import io
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from servicepulse.faults import read_faults
from servicepulse.imports import import_parquet
from servicepulse.measurements import numeric_columns
from servicepulse.presentation import (
    CATEGORIES,
    FAULTS,
    display_frame,
    faults_export,
    measurement_figure,
    unit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_translations_cover_source_and_preserve_originals():
    frame = read_faults(ROOT / "fault_summary_R1.xlsx")
    original = frame.copy(deep=True)
    assert set(frame.category).issubset(CATEGORIES)
    assert set(frame.fault_text).issubset(FAULTS)
    display = display_frame(frame[["device_id", "event_date", "category", "fault_text"]])
    assert list(display.columns) == [
        "Geräte-ID",
        "Servicedatum",
        "Fehlerkategorie",
        "Dokumentierter Anlass",
    ]
    assert display.iloc[0]["Servicedatum"] == "13.02.2015"
    exported = pd.read_csv(io.BytesIO(faults_export(frame)))
    assert set(frame.columns).issubset(exported.columns)
    assert exported["Fault categories"].tolist() == frame["Fault categories"].tolist()
    assert exported.main_fault.tolist() == frame.main_fault.tolist()
    assert "Kältemittelleckage" in exported["Fehlerkategorie (Deutsch)"].tolist()
    pd.testing.assert_frame_equal(frame, original)


def test_german_curve_has_units_uncertainty_day_and_visible_gaps():
    assert unit("Mains Voltage") == "V"
    assert unit("unknown_new_sensor") == "Einheit nicht angegeben"
    source = pd.DataFrame(
        {
            "time": pd.to_datetime(["2022-06-28 00:00", "2022-06-28 02:00"]),
            "mean": [-80.0, -78.0],
            "minimum": [-81.0, -79.0],
            "maximum": [-79.0, -77.0],
            "n": [2, 2],
        }
    )
    original = source.copy(deep=True)
    figure = measurement_figure(source, "RTD", "hour", [pd.Timestamp("2022-06-28")])
    assert {trace.name for trace in figure.data} == {"Mittelwert", "Minimum", "Maximum"}
    assert "°C" in figure.layout.yaxis.title.text
    assert all(not trace.connectgaps for trace in figure.data)
    assert all(pd.isna(trace.y[1]) for trace in figure.data)
    assert pd.Timestamp(figure.layout.shapes[0].x1) - pd.Timestamp(
        figure.layout.shapes[0].x0
    ) == pd.Timedelta(days=1)
    pd.testing.assert_frame_equal(source, original)


def parquet_content(frame):
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def test_import_and_overwrite_protection(tmp_path):
    content = parquet_content(
        pd.DataFrame({"Datetime": pd.to_datetime(["2022-01-01"]), "RTD": [-80.0]})
    )
    path, digest = import_parquet(content, "123456_temp.parquet", tmp_path)
    assert path.read_bytes() == content and len(digest) == 64
    with pytest.raises(ValueError, match="nicht überschrieben"):
        import_parquet(content, "123456_temp.parquet", tmp_path)
    assert path.read_bytes() == content


@pytest.mark.parametrize(
    "name,content",
    [
        ("../123456_temp.parquet", b"not parquet"),
        ("123456_temp.parquet", b"not parquet"),
        (
            "123456_temp.parquet",
            parquet_content(pd.DataFrame({"Datetime": ["2022-01-01"], "RTD": [-80.0]})),
        ),
        (
            "123456_temp.parquet",
            parquet_content(
                pd.DataFrame({"Datetime": pd.to_datetime(["2022-01-01"]), "State": [3]})
            ),
        ),
    ],
)
def test_invalid_import_does_not_write_files(tmp_path, name, content):
    with pytest.raises(ValueError):
        import_parquet(content, name, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_numeric_measurements_exclude_event_lists(tmp_path):
    path = tmp_path / "123456_temp.parquet"
    pd.DataFrame(
        {"Datetime": pd.to_datetime(["2022-01-01"]), "RTD": [-80.0], "Type": [[3, 5]], "State": [3]}
    ).to_parquet(path, index=False)
    assert numeric_columns(path) == ["RTD"]


def test_german_sections_and_preserved_metrics():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception and not app.error
    assert [tab.label for tab in app.tabs] == [
        "Übersicht",
        "Geräte & Serviceberichte",
        "Betriebsanalyse & Vergleiche",
        "Datenqualität & Forschung",
    ]
    assert [metric.value for metric in app.metric[:4]] == ["46", "24", "11", "5"]
    assert "Kältemittelleckage" in app.multiselect(key="categories").format_func(
        "Refrigerant leakage"
    )
    assert any(expander.label.startswith("Erweiterte Funktion") for expander in app.expander)
    if not any(widget.key == "measurement_device" for widget in app.selectbox):
        return
    assert all(
        "/" not in label and "\\" not in label
        for label in app.selectbox(key="measurement_device").options
    )
