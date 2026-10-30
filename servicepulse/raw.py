"""Eigene Rohdatenleser für kontrollierte Stichproben, unabhängig vom Autorencode.

Keine automatische Vollrekonstruktion der veröffentlichten Parquet-Daten.
Unsichere Zuordnungen werden ausgewiesen statt durch Positionsjoins verdeckt.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pandas as pd


def read_revco_temperature(
    path: str | Path, device_id: str, offset: pd.Timedelta = pd.Timedelta(0)
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Liest einen Revco-Rohtext und liefert Messwerte sowie einen Bericht zu ID- und Zeitproblemen."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    header = next(
        (
            i
            for i, line in enumerate(lines)
            if "Date" in line.split("\t") and "RTD" in line.split("\t")
        ),
        None,
    )
    if header is None:
        raise ValueError("Keine Revco-Kopfzeile mit Date und RTD gefunden")
    match = re.search(r"Unit Name\s*:\s*(\S+)", "\n".join(lines[:header]))
    declared_id = match[1] if match else None
    frame = pd.read_csv(path, sep="\t", skiprows=header)
    required = ["Date", "Time", "RTD"]
    if not set(required).issubset(frame.columns):
        raise ValueError("Revco-Pflichtspalten fehlen")
    frame["Datetime_internal"] = pd.to_datetime(
        frame.Date.astype("string") + " " + frame.Time.astype("string"),
        format="%m/%d/%Y %H:%M:%S",
        errors="coerce",
    )
    frame["Datetime"] = frame.Datetime_internal + offset
    frame["RTD"] = pd.to_numeric(frame.RTD, errors="coerce")
    frame["device_id"] = str(device_id)
    report = {
        "source": str(path),
        "rows": len(frame),
        "declared_unit_name": declared_id,
        "folder_device_id": str(device_id),
        "identifier_conflict": declared_id is not None and declared_id != str(device_id),
        "invalid_times": int(frame.Datetime.isna().sum()),
        "invalid_rtd": int(frame.RTD.isna().sum()),
        "duplicate_times": int(frame.Datetime.duplicated().sum()),
    }
    return frame, report


def read_haier_temperature(
    path: str | Path,
    device_id: str,
    offset: pd.Timedelta = pd.Timedelta(0),
    tolerance_seconds: int = 2,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Liest die originale Haier-Datei schreibgeschützt; ordnet Sensoren kontrolliert nach Zeit zu."""
    # sqlite3s Transaktionskontext schließt die Verbindung nicht selbst.
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as con:
        sensors = pd.read_sql_query("SELECT * FROM EACH_POINT_DATA_CHANGE", con)
        rtd = pd.read_sql_query("SELECT TIME, TEMPERATURE FROM TEMPER_RECORD", con)
    if sensors.TIME.duplicated().any() or rtd.TIME.duplicated().any():
        raise ValueError("Mehrdeutige Haier-Zeitstempel: vor Zuordnung manuell klären")
    positional_mismatches = (
        int(sensors.TIME.ne(rtd.TIME).sum()) if len(sensors) == len(rtd) else None
    )
    sensors["Datetime_internal"] = pd.to_datetime(
        sensors.TIME, format="%Y-%m-%d %H:%M:%S", errors="raise"
    )
    rtd["RTD_time_internal"] = pd.to_datetime(rtd.TIME, format="%Y-%m-%d %H:%M:%S", errors="raise")
    rtd = rtd.rename(columns={"TEMPERATURE": "RTD"})
    frame = pd.merge_asof(
        sensors.sort_values("Datetime_internal"),
        rtd[["RTD_time_internal", "RTD"]].sort_values("RTD_time_internal"),
        left_on="Datetime_internal",
        right_on="RTD_time_internal",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=tolerance_seconds),
    )
    frame["match_distance_seconds"] = (
        (frame.Datetime_internal - frame.RTD_time_internal).dt.total_seconds().abs()
    )
    frame["Datetime"] = frame.Datetime_internal + offset
    frame["device_id"] = str(device_id)
    reused = frame.RTD_time_internal.dropna().duplicated(keep=False)
    if reused.any():
        raise ValueError("Haier-Zuordnung verwendet RTD-Zeit mehrfach; Toleranz oder Daten prüfen")
    return frame, {
        "source": str(path),
        "rows": len(frame),
        "positional_time_mismatches": positional_mismatches,
        "unmatched_rtd": int(frame.RTD_time_internal.isna().sum()),
        "tolerance_seconds": tolerance_seconds,
        "max_match_distance_seconds": float(frame.match_distance_seconds.max()),
    }
