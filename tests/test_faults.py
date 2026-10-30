from pathlib import Path

import pandas as pd
import pytest

from servicepulse.faults import (
    category_control,
    compare_reference,
    filter_faults,
    metrics,
    read_faults,
)

ROOT = Path(__file__).resolve().parents[1]


def test_real_workbook():
    df = read_faults(ROOT / "fault_summary_R1.xlsx")
    assert metrics(df) == dict(
        entries=46,
        devices=24,
        devices_multiple_entries=11,
        repeated_device_category_pairs=5,
        invalid_dates=0,
        duplicate_rows=0,
    )
    assert df.category_group.eq("Refrigerant leakage").sum() == 11
    assert df.category.eq("Data missing").sum() == 4
    assert df.source_row.min() == 2 and df.source_row.max() == 47


def test_real_category_control_sheet():
    path = ROOT / "fault_summary_R1.xlsx"
    compared = category_control(path, read_faults(path))
    assert len(compared) == 10
    assert compared.matches.all()
    assert compared.calculated_count.sum() == 46


def test_filter_inclusive_end_and_empty_selection():
    df = read_faults(ROOT / "fault_summary_R1.xlsx")
    result = filter_faults(df, ["806018"], ["Refrigerant leakage"], "2022-10-04", "2022-10-04")
    assert len(result) == 1
    assert filter_faults(df, devices=[]).empty
    assert filter_faults(df, categories=[]).empty
    assert metrics(df.iloc[:0])["entries"] == 0


def test_bad_and_empty_workbooks(tmp_path):
    bad = tmp_path / "bad.xlsx"
    pd.DataFrame({"unexpected": [1]}).to_excel(bad, index=False)
    with pytest.raises(ValueError, match="Datenblatt"):
        read_faults(bad)
    pd.DataFrame(
        columns=["freezer_id", "registered_date", "main_fault", "Fault categories"]
    ).to_excel(bad, index=False)
    assert read_faults(bad).empty


def test_invalid_fields_duplicates_and_whitespace(tmp_path):
    # Ausschließlich künstliche Testfixture, keine Forschungsdaten.
    bad = tmp_path / "test.xlsx"
    pd.DataFrame(
        {
            "freezer_id": ["invalid", "invalid"],
            "registered_date": ["03/04/2020"] * 2,
            "main_fault": ["x"] * 2,
            "Fault categories": [" x (No fix) "] * 2,
        }
    ).to_excel(bad, index=False)
    df = read_faults(bad)
    assert df.event_date.isna().all()
    assert not df.device_valid.any()
    assert df.duplicate.all()
    assert df.category_group.eq("x").all()
    assert df.no_fix.all()


@pytest.mark.local_data
def test_source_conflicts_are_retained():
    ref = ROOT / "research/reference/data/raw_data/other_data/freezer_faults.csv"
    if not ref.exists():
        pytest.skip("Optionale Autorenreferenz fehlt")
    df = read_faults(ROOT / "fault_summary_R1.xlsx")
    comparison = compare_reference(df, ref)
    assert comparison.reference_status.ne("Übereinstimmung").sum() == 3
    assert df.loc[
        (df.device_id == "806031") & (df.fault_text == "filter_drier"), "event_date"
    ].item() == pd.Timestamp("2023-02-03")
