"""Validierender lokaler Import; vorhandene Dateien werden nie überschrieben."""
from pathlib import Path
import io
import re
import hashlib
import pyarrow as pa
import pyarrow.parquet as pq

def import_parquet(content, filename, directory):
    if not re.fullmatch(r'\d{6}_(temp|events)\.parquet',filename):
        raise ValueError('Der Dateiname muss Geräte-ID und Dateiart enthalten, zum Beispiel 806279_temp.parquet.')
    if len(content) > 300*1024*1024:
        raise ValueError('Die Datei ist größer als 300 MB. Bitte nach Anleitung direkt in den Messdatenordner kopieren.')
    try:
        schema = pq.ParquetFile(io.BytesIO(content)).schema_arrow
    except Exception as exc:
        raise ValueError('Die Datei ist keine lesbare Parquet-Datei.') from exc
    if 'Datetime' not in schema.names or not pa.types.is_timestamp(schema.field('Datetime').type):
        raise ValueError('Die Datei benötigt die Originalspalte Datetime im Zeitstempelformat.')
    if filename.endswith('_temp.parquet') and not any(
        (pa.types.is_integer(field.type) or pa.types.is_floating(field.type) or pa.types.is_decimal(field.type))
        and field.name not in {'index','__index_level_0__','State'} for field in schema):
        raise ValueError('Die Datei enthält keine geeignete numerische Messgröße.')
    destination = Path(directory)/filename
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        with destination.open('xb') as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ValueError('Diese Datei ist bereits vorhanden. Sie wurde nicht überschrieben.') from exc
    return destination,hashlib.sha256(content).hexdigest()
