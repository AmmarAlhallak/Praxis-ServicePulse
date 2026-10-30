"""Filterzustand, belegbare Falltexte und Aktualität von Prüfprotokollen."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Sequence

import pandas as pd

from servicepulse.faults import filter_faults
from servicepulse.presentation import german_number

QUESTION = (
    "Wie lassen sich historische Serviceeinträge und Betriebszeitreihen von Ultratiefkühlgeräten "
    "nachvollziehbar aufbereiten und interaktiv untersuchen, sodass Störungshäufigkeiten, "
    "wiederkehrende Einträge, Temperaturverläufe und Datenlücken sichtbar werden?"
)
DEMO_CASES = {
    "temperature": ("806279", "2022-06-28", "Temperaturveränderung"),
    "gap": ("806030", "2015-01-28", "Messlücke"),
    "conflict": ("806031", "2023-02-03", "Datumswiderspruch"),
}


def apply_service_selection(
    df: pd.DataFrame,
    devices: Sequence[str] | None = None,
    categories: Sequence[str] | None = None,
    limit_dates: bool = False,
    start: date | None = None,
    end: date | None = None,
    include_undated: bool = True,
) -> tuple[pd.DataFrame, str | None]:
    """Prüft Servicefilter und liefert die Auswahl plus einen verständlichen Zeitraumfehler."""
    selected = filter_faults(df, devices, categories)
    if limit_dates:
        if start is None or end is None:
            return (
                selected.iloc[:0].copy(),
                "Zeitraum unvollständig: Bitte Start- und Enddatum angeben. Bis dahin werden keine Serviceeinträge ausgewählt.",
            )
        if pd.Timestamp(start) > pd.Timestamp(end):
            return (
                selected.iloc[:0].copy(),
                "Das Startdatum liegt nach dem Enddatum. Bitte den Zeitraum korrigieren; aktuell sind keine Serviceeinträge ausgewählt.",
            )
        dated = filter_faults(selected, start=start, end=end)
        selected = (
            pd.concat([dated, selected[selected.event_date.isna()]]) if include_undated else dated
        )
    elif not include_undated:
        selected = selected[selected.event_date.notna()]
    return selected.copy(), None


def case_observation(comparison: pd.DataFrame, day: pd.Series, column_unit: str) -> str:
    """Beschreibt vorhandene Vergleichswerte mit Stichprobenzahlen und fachlichen Grenzen."""
    before, after = comparison.iloc[0], comparison.iloc[1]
    if before.valid == 0 or after.valid == 0:
        return (
            f"Am Servicetag liegen {german_number(day.valid)} gültige Messpunkte vor. "
            f"Vorher sind es {german_number(before.valid)}, nachher {german_number(after.valid)}. "
            "Mindestens ein Vergleichsfenster ist leer; ein Vorher-Nachher-Unterschied kann dafür nicht berechnet werden."
        )
    difference = after["mean"] - before["mean"]
    direction = "niedriger" if difference < 0 else "höher" if difference > 0 else "gleich"
    return (
        f"Der beobachtete Durchschnitt liegt nach dem Servicetag um {german_number(abs(difference), 2)} "
        f"{column_unit} {direction}: vorher {german_number(before['mean'], 2)}, "
        f"nachher {german_number(after['mean'], 2)} {column_unit}. "
        f"Dafür stehen {german_number(before.valid)} bzw. {german_number(after.valid)} gültige Messpunkte zur Verfügung. "
        "Die Aussage gilt ausschließlich für die vorhandenen Messwerte, nicht für unbeobachtete Zeiten oder eine Reparaturwirkung."
    )


def coverage_rows(comparison: pd.DataFrame, day: pd.Series, days: int) -> pd.DataFrame:
    """Stellt gültige Punkte und beobachtete Stunden der drei Vergleichsfenster gegenüber."""
    records = []
    for label, row, hours in [
        ("Vorher", comparison.iloc[0], days * 24),
        ("Servicetag", day, 24),
        ("Nachher", comparison.iloc[1], days * 24),
    ]:
        observed = int(row.observed_hours)
        records.append(
            {
                "Zeitraum": label,
                "Gültige Messpunkte": int(row.valid),
                "Stunden mit Messpunkten": observed,
                "Stunden ohne Messpunkte": hours - observed,
            }
        )
    return pd.DataFrame(records)


def inputs_fingerprint(source: str | Path, files: pd.DataFrame) -> str:
    """Aktualitätskennung, kein Ersatz für fachliche Datenvalidierung."""
    records = [
        (str(Path(p).resolve()), Path(p).stat().st_size, Path(p).stat().st_mtime_ns)
        for p in sorted(files.path)
    ]
    digest = hashlib.sha256(Path(source).read_bytes())
    digest.update(json.dumps(records).encode("utf-8"))
    return digest.hexdigest()


def read_test_report(root: str | Path) -> dict[str, int] | None:
    """Liefert nur einen gegenüber dem gesamten Python-Code aktuellen lokalen Testbericht."""
    root = Path(root)
    candidates = [
        root / "docs" / name
        for name in ["testlauf_review.xml", "testlauf_postgresql.xml", "testlauf_praxis.xml"]
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    path = max(existing, key=lambda candidate: candidate.stat().st_mtime)
    sources = [
        root / "app.py",
        *root.glob("servicepulse/**/*.py"),
        *root.glob("tests/*.py"),
        *root.glob("scripts/*.py"),
        *root.glob("migrations/**/*.py"),
    ]
    if any(p.stat().st_mtime > path.stat().st_mtime for p in sources):
        return None
    try:
        suites = list(ET.parse(path).getroot().iter("testsuite"))
        result = {
            key: sum(int(s.get(key, "0")) for s in suites)
            for key in ["tests", "failures", "errors", "skipped"]
        }
        result["passed"] = (
            result["tests"] - result["failures"] - result["errors"] - result["skipped"]
        )
        return result
    except (ET.ParseError, ValueError, OSError):
        return None
