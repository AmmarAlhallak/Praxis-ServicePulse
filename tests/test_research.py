"""Regressionsprüfungen für vollständige Filter und belegte Untersuchungsfälle."""

import os
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from servicepulse.faults import read_faults
from servicepulse.measurements import serviceday_summary, window_comparison
from servicepulse.research import (
    apply_service_selection,
    case_observation,
    coverage_rows,
    inputs_fingerprint,
    read_test_report,
)

ROOT = Path(__file__).resolve().parents[1]


def test_explicit_all_and_invalid_service_periods():
    df = read_faults(ROOT / "fault_summary_R1.xlsx")
    actual, error = apply_service_selection(df)
    assert error is None
    pd.testing.assert_frame_equal(df, actual)
    assert apply_service_selection(df, devices=[])[0].empty
    assert apply_service_selection(df, limit_dates=True, start=date(2022, 1, 1), end=None)[0].empty
    assert (
        "unvollständig"
        in apply_service_selection(df, limit_dates=True, start=date(2022, 1, 1), end=None)[1]
    )
    assert (
        "nach dem Enddatum"
        in apply_service_selection(
            df, limit_dates=True, start=date(2023, 1, 1), end=date(2022, 1, 1)
        )[1]
    )
    filtered, error = apply_service_selection(
        df, ["806279"], ["Refrigerant leakage"], True, date(2022, 6, 28), date(2022, 6, 28)
    )
    assert error is None and len(filtered) == 1


def test_default_filters_have_no_chips_or_end_date_warning():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception and not app.error
    assert (
        app.multiselect(key="devices").value == [] and app.multiselect(key="categories").value == []
    )
    assert app.checkbox(key="all_devices").value and app.checkbox(key="all_categories").value
    assert not app.checkbox(key="limit_service_dates").value
    assert app.date_input(key="service_start").value == date(2014, 7, 29)
    assert app.date_input(key="service_end").value == date(2023, 4, 12)
    assert [m.value for m in app.metric[:4]] == ["46", "24", "11", "5"]
    assert not any("Enddatum auswählen" in element.value for element in app.info)
    # Ein alter gespeicherter Range-Wert darf die neuen skalaren Filter nicht beeinflussen.
    app.session_state["date_range"] = (date(2014, 7, 29),)
    app.run()
    assert app.metric[0].value == "46"
    assert not any("Enddatum auswählen" in element.value for element in app.info)


def test_incomplete_reversed_and_reset_dates_in_ui():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.checkbox(key="limit_service_dates").check().run()
    app.date_input(key="service_end").set_value(None).run()
    assert not app.exception and app.metric[0].value == "0"
    assert any("unvollständig" in warning.value for warning in app.warning)
    app.date_input(key="service_start").set_value(date(2023, 4, 12))
    app.date_input(key="service_end").set_value(date(2014, 7, 29)).run()
    assert not app.exception and app.metric[0].value == "0"
    assert any("nach dem Enddatum" in warning.value for warning in app.warning)
    next(b for b in app.button if b.label == "Alle Filter zurücksetzen").click().run()
    assert app.metric[0].value == "46" and not app.checkbox(key="limit_service_dates").value


@pytest.mark.local_data
def test_demonstration_buttons_select_real_cases_and_do_not_change_service_filters():
    for device in ["806279", "806030", "806031"]:
        if not (ROOT / f"data/raw/Revco/{device}_temp.parquet").exists():
            pytest.skip("Optionale reale Fall-Messdatei fehlt")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    app.checkbox(key="all_devices").uncheck().run()
    assert app.metric[0].value == "0"
    app.button(key="demo_gap").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="measurement_device").value == "806030"
    assert app.selectbox(key="managed_device").value == "806030"
    assert app.metric[0].value == "0"
    coverage = next(t.value for t in app.dataframe if "Stunden ohne Messpunkte" in t.value.columns)
    assert coverage["Gültige Messpunkte"].tolist() == [0, 24, 0]
    assert coverage["Stunden ohne Messpunkte"].tolist() == [168, 22, 168]
    app.button(key="demo_conflict").click().run()
    assert not app.exception and any("Datumswiderspruch" in w.value for w in app.warning)
    app.button(key="demo_temperature").click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key="measurement_device").value == "806279"
    assert app.selectbox(key="measure_806279").value == "RTD"
    assert app.slider(key="comparison_days").value == 7
    coverage = next(t.value for t in app.dataframe if "Stunden ohne Messpunkte" in t.value.columns)
    assert coverage["Gültige Messpunkte"].tolist() == [2869, 1440, 10075]
    assert coverage["Stunden mit Messpunkten"].tolist() == [49, 24, 168]


@pytest.mark.local_data
def test_real_case_statistics_and_text_preserve_missingness():
    for device, day, expected in [
        ("806279", "2022-06-28", [2869, 1440, 10075]),
        ("806030", "2015-01-28", [0, 24, 0]),
    ]:
        path = ROOT / f"data/raw/Revco/{device}_temp.parquet"
        if not path.exists():
            pytest.skip("Optionale Messdatei fehlt")
        comparison = window_comparison(path, "RTD", day)
        summary = serviceday_summary(path, "RTD", day)
        assert coverage_rows(comparison, summary, 7)["Gültige Messpunkte"].tolist() == expected
        text = case_observation(comparison, summary, "°C")
        if device == "806279":
            assert comparison.iloc[0]["minimum"] == pytest.approx(-80.7)
            assert comparison.iloc[1]["maximum"] == pytest.approx(-65.7)
            assert "15,89" in text and "Reparaturwirkung" in text
        else:
            assert comparison["mean"].isna().all()
            assert "kann dafür nicht berechnet werden" in text


def test_proof_freshness_and_inputs_fingerprint(tmp_path):
    # Ausschließlich kleine künstliche Prüfdateien im Testverzeichnis.
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"source fixture")
    files = pd.DataFrame(columns=["path"])
    first = inputs_fingerprint(source, files)
    source.write_bytes(b"changed fixture")
    assert first != inputs_fingerprint(source, files)
    (tmp_path / "docs").mkdir()
    app = tmp_path / "app.py"
    app.write_text("# test fixture")
    proof = tmp_path / "docs/testlauf_praxis.xml"
    proof.write_text(
        '<testsuites><testsuite tests="4" failures="0" errors="0" skipped="1" /></testsuites>'
    )
    os.utime(app, (100, 100))
    os.utime(proof, (200, 200))
    assert read_test_report(tmp_path)["passed"] == 3
    os.utime(app, (300, 300))
    assert read_test_report(tmp_path) is None
