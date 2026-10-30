"""Begrenzte DuckDB-Parquet-Abfragen statt Vollimport großer Messdateien."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def quote_identifier(name: str) -> str:
    """Maskiert einen geprüften SQL-Spaltennamen; Werte werden separat parametrisiert."""
    return '"' + name.replace('"', '""') + '"'


def validate_time_column(schema: pa.Schema) -> None:
    """Prüft die gemeinsame Zeitbasis; keine stillschweigende Zeitzonenumdeutung."""
    if "Datetime" not in schema.names or not pa.types.is_timestamp(schema.field("Datetime").type):
        raise ValueError("Datetime muss als Zeitstempel gespeichert sein.")
    if schema.field("Datetime").type.tz is not None:
        raise ValueError(
            "Zeitstempel mit Zeitzone benötigen vor dem Import eine ausdrücklich dokumentierte Zeitumrechnung. Die Forschungszeitbasis hat keine bestätigte Zeitzone."
        )


def inspect_file(path: str | Path) -> dict[str, Any]:
    """Liefert validierte Parquet-Metadaten, ohne alle Messwerte einzulesen."""
    path = Path(path)
    match = re.fullmatch(r"(\d{6})_(temp|events)\.parquet", path.name)
    if not match:
        raise ValueError(
            "Dateiname muss <sechsstellige Geräte-ID>_temp.parquet oder _events.parquet entsprechen."
        )
    schema = pq.ParquetFile(path)
    validate_time_column(schema.schema_arrow)
    if match[2] == "temp" and not any(
        (
            pa.types.is_integer(field.type)
            or pa.types.is_floating(field.type)
            or pa.types.is_decimal(field.type)
        )
        and field.name not in ["index", "__index_level_0__", "State"]
        for field in schema.schema_arrow
    ):
        raise ValueError("Temperaturdatei enthält keine numerische Messgröße.")
    return dict(
        path=str(path.resolve()),
        device_id=match[1],
        kind=match[2],
        model=path.parent.name,
        rows=schema.metadata.num_rows,
        columns=", ".join(schema.schema_arrow.names),
    )


def inventory(root: str | Path) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Liefert ein Dateiinventar und getrennte Lesefehler; verändert keine Dateien."""
    rows, errors = [], []
    for path in sorted(Path(root).rglob("*.parquet")):
        try:
            rows.append(inspect_file(path))
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    return pd.DataFrame(
        rows, columns=["path", "device_id", "kind", "model", "rows", "columns"]
    ), errors


def numeric_columns(path: str | Path) -> list[str]:
    """Liefert numerische Messgrößen; Zustandsbits und technische Indizes sind ausgeschlossen."""
    with duckdb.connect() as con:
        description = con.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()
    # State ist ein Bitcode. Ein arithmetischer Mittelwert wäre kein Gerätezustand.
    scalar_number = (
        r"(?:U?(?:TINYINT|SMALLINT|INTEGER|BIGINT|HUGEINT)|FLOAT|DOUBLE|DECIMAL\(\d+,\s*\d+\))"
    )
    return [
        name
        for name, kind, *_ in description
        if re.fullmatch(scalar_number, kind) and name not in ["index", "__index_level_0__", "State"]
    ]


def time_bounds(path: str | Path) -> tuple[datetime | None, datetime | None]:
    """Liefert den ersten und letzten gültigen Zeitstempel einer Messdatei."""
    with duckdb.connect() as con:
        return con.execute(
            'SELECT min("Datetime"), max("Datetime") FROM read_parquet(?)', [str(path)]
        ).fetchone()


def series_window(
    path: str | Path,
    column: str,
    start: str | date | pd.Timestamp,
    end: str | date | pd.Timestamp,
    bucket: str = "hour",
) -> pd.DataFrame:
    """Aggregiert das halboffene Zeitfenster [Start, Ende), ohne Lücken aufzufüllen."""
    if column not in numeric_columns(path):
        raise ValueError("Unbekannte oder nicht numerische Messgröße.")
    if bucket not in {"minute", "hour", "day"}:
        raise ValueError("Ungültiges Aggregationsintervall.")
    col = quote_identifier(column)
    with duckdb.connect() as con:
        return con.execute(
            f"""SELECT date_trunc('{bucket}', "Datetime") AS time,
          avg({col}) AS mean, min({col}) AS minimum, max({col}) AS maximum,
          count({col}) AS n FROM read_parquet(?)
          WHERE "Datetime" >= ? AND "Datetime" < ?
          GROUP BY 1 ORDER BY 1""",
            [str(path), pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime()],
        ).df()


def event_window(
    path: str | Path,
    start: str | date | pd.Timestamp,
    end: str | date | pd.Timestamp,
    offset: pd.Timedelta = pd.Timedelta(0),
    limit: int = 1000,
) -> pd.DataFrame:
    """Separate Ereignisdateien enthalten laut Autorenpipeline interne Uhrzeiten."""
    with duckdb.connect() as con:
        df = con.execute(
            """SELECT * FROM read_parquet(?) WHERE "Datetime" >= ? AND "Datetime" < ? ORDER BY "Datetime" LIMIT ?""",
            [
                str(path),
                (pd.Timestamp(start) - offset).to_pydatetime(),
                (pd.Timestamp(end) - offset).to_pydatetime(),
                limit,
            ],
        ).df()
    df["Datetime_internal"] = df.Datetime
    df["Datetime"] = df.Datetime + offset
    return df


def offsets(path: str | Path) -> dict[str, pd.Timedelta]:
    """Liest die dokumentierten gerätebezogenen Uhrkorrekturen der Autoren."""
    df = pd.read_csv(path, dtype={"freezer_id": "string"})
    delta = pd.to_datetime(df.actual_time, format="%m/%d/%Y %H:%M:%S") - pd.to_datetime(
        df.internal_time, format="%m/%d/%Y %H:%M:%S"
    )
    return dict(zip(df.freezer_id, delta))


def window_comparison(
    path: str | Path, column: str, date: str | date | pd.Timestamp, days: int = 7
) -> pd.DataFrame:
    """Ereignistag vollständig ausschließen; Stichprobenzahlen statt Kausalbehauptung."""
    date = pd.Timestamp(date).normalize()
    col = quote_identifier(column)
    if column not in numeric_columns(path):
        raise ValueError("Unbekannte Messgröße")
    rows = []
    with duckdb.connect() as con:
        for label, start, end in [
            ("Vorher", date - pd.Timedelta(days=days), date),
            ("Nachher", date + pd.Timedelta(days=1), date + pd.Timedelta(days=days + 1)),
        ]:
            row = con.execute(
                f"""SELECT count(*) AS rows, count({col}) AS valid,
              avg({col}) AS mean, median({col}) AS median,
              min({col}) AS minimum, max({col}) AS maximum,
              count(DISTINCT date_trunc('hour', "Datetime")) FILTER (WHERE {col} IS NOT NULL) AS observed_hours,
              min("Datetime") AS first_time,
              max("Datetime") AS last_time FROM read_parquet(?) WHERE "Datetime" >= ? AND "Datetime" < ?""",
                [str(path), start.to_pydatetime(), end.to_pydatetime()],
            ).df()
            row.insert(0, "window", label)
            rows.append(row)
    return pd.concat(rows, ignore_index=True)


def serviceday_summary(path: str | Path, column: str, date: str | date | pd.Timestamp) -> pd.Series:
    """Liefert Messanzahl und Kenngrößen ausschließlich für den vollständigen Servicetag."""
    if column not in numeric_columns(path):
        raise ValueError("Unbekannte Messgröße")
    date = pd.Timestamp(date).normalize()
    col = quote_identifier(column)
    with duckdb.connect() as con:
        return (
            con.execute(
                f"""SELECT count(*) AS rows, count({col}) AS valid,
          avg({col}) AS mean, min({col}) AS minimum, max({col}) AS maximum,
          count(DISTINCT date_trunc('hour', "Datetime")) FILTER (WHERE {col} IS NOT NULL) AS observed_hours
          FROM read_parquet(?) WHERE "Datetime" >= ? AND "Datetime" < ?""",
                [str(path), date.to_pydatetime(), (date + pd.Timedelta(days=1)).to_pydatetime()],
            )
            .df()
            .iloc[0]
        )


def audit_file(path: str | Path) -> dict[str, Any]:
    """Vollständige Zeit-/RTD-Prüfung einer Datei, ohne Messdaten zu persistieren."""
    meta = inspect_file(path)
    has_rtd = "RTD" in pq.ParquetFile(path).schema_arrow.names
    extra = (
        ", count(*) FILTER (WHERE RTD IS NULL) AS missing_rtd, min(RTD) AS min_rtd, max(RTD) AS max_rtd"
        if has_rtd
        else ""
    )
    with duckdb.connect() as con:
        result = (
            con.execute(
                f"""SELECT count(*) AS rows, min("Datetime") AS first_time,
          max("Datetime") AS last_time, count(*) FILTER (WHERE "Datetime" IS NULL) AS null_times,
          count("Datetime") - count(DISTINCT "Datetime") AS repeated_timestamps {extra}
          FROM read_parquet(?)""",
                [str(path)],
            )
            .df()
            .iloc[0]
            .to_dict()
        )
        gaps = (
            con.execute(
                """SELECT max(gap) AS max_gap_seconds, median(gap) AS median_gap_seconds,
          count(*) FILTER (WHERE gap > 86400) AS gaps_over_day FROM
          (SELECT epoch("Datetime" - lag("Datetime") OVER (ORDER BY "Datetime")) AS gap FROM read_parquet(?))""",
                [str(path)],
            )
            .df()
            .iloc[0]
            .to_dict()
        )
    return {**meta, **result, **gaps}
