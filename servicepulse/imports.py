"""Validierender lokaler Import; vorhandene Dateien werden nie überschrieben."""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from servicepulse.measurements import validate_time_column


def import_parquet(
    content: bytes,
    filename: str,
    directory: str | Path,
    registry: pd.DataFrame | None = None,
    source: str | None = None,
) -> tuple[Path, str]:
    """Validiert einen Upload, schreibt eine neue Datei und liefert Pfad sowie Inhaltshash."""
    if not re.fullmatch(r"\d{6}_(temp|events)\.parquet", filename):
        raise ValueError(
            "Der Dateiname muss Geräte-ID und Dateiart enthalten, zum Beispiel 806279_temp.parquet."
        )
    if len(content) > 300 * 1024 * 1024:
        raise ValueError(
            "Die Datei ist größer als 300 MB. Bitte nach Anleitung direkt in den Messdatenordner kopieren."
        )
    try:
        schema = pq.ParquetFile(io.BytesIO(content)).schema_arrow
    except Exception as exc:
        raise ValueError("Die Datei ist keine lesbare Parquet-Datei.") from exc
    validate_time_column(schema)
    if filename.endswith("_temp.parquet") and not any(
        (
            pa.types.is_integer(field.type)
            or pa.types.is_floating(field.type)
            or pa.types.is_decimal(field.type)
        )
        and field.name not in {"index", "__index_level_0__", "State"}
        for field in schema
    ):
        raise ValueError("Die Datei enthält keine geeignete numerische Messgröße.")
    times = pq.read_table(io.BytesIO(content), columns=["Datetime"]).column("Datetime")
    if times.null_count or not len(times):
        raise ValueError("Die Datei enthält fehlende Zeitstempel oder keine Messwerte.")
    digest = hashlib.sha256(content).hexdigest()
    if registry is not None:
        if not source or not source.strip():
            raise ValueError("Bitte Herkunft und Nutzungsrecht angeben.")
        from servicepulse.repository import digest_file

        for row in registry.itertuples():
            registered = getattr(row, "sha256", None)
            if registered == digest or (
                registered is None and Path(row.path).exists() and digest_file(row.path) == digest
            ):
                raise ValueError(
                    "Identische Messdatei ist bereits vorhanden; kein doppelter Import."
                )
    destination = Path(directory) / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ValueError(
            "Diese Datei ist bereits vorhanden. Sie wurde nicht überschrieben."
        ) from exc
    return destination, digest
