"""Lokale Excel, DuckDB und Parquet-Metadaten schreibgeschützt abgleichen.

Offline ausführbar, auch aus einem anderen Arbeitsordner. Messdaten bleiben extern.
Ein Fehler führt zu Exitcode 1; es wird nichts automatisch neu aufgebaut.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from datetime import datetime, timezone
import duckdb
import pandas as pd
from servicepulse.faults import read_faults, quality, metrics, category_control
from servicepulse.measurements import inventory
from servicepulse.research import inputs_fingerprint

ROOT = Path(__file__).resolve().parents[1]

def check(root=ROOT):
    root = Path(root)
    faults = read_faults(root / 'fault_summary_R1.xlsx')
    files, file_errors = inventory(root / 'data/raw')
    database = root / 'data/processed/servicepulse.duckdb'
    if not database.exists():
        raise FileNotFoundError(f'DuckDB fehlt: {database}. scripts/build.py ausführen.')
    control = category_control(root / 'fault_summary_R1.xlsx', faults)
    if not control.empty and not control.matches.all():
        raise ValueError('Das Excel-Kontrollblatt widerspricht den Einzelzeilen.')
    if file_errors:
        raise ValueError(f'Nicht lesbare Parquet-Dateien: {file_errors}')
    with duckdb.connect(str(database), read_only=True) as connection:
        stored = connection.execute('SELECT * FROM faults ORDER BY source_row').df()
        # Datentypen des Dateiformats dürfen sich unterscheiden; Inhalte nicht.
        pd.testing.assert_frame_equal(faults.sort_values('source_row').reset_index(drop=True), stored,
                                      check_dtype=False)
        stored_files = connection.execute('SELECT * FROM measurement_files ORDER BY path').df()
        pd.testing.assert_frame_equal(files.sort_values('path').reset_index(drop=True), stored_files,
                                      check_dtype=False)
        stored_quality = connection.execute('SELECT * FROM quality_checks ORDER BY "Prüfung"').df()
        pd.testing.assert_frame_equal(quality(faults).sort_values('Prüfung').reset_index(drop=True),
                                      stored_quality, check_dtype=False)
        categories = connection.execute('SELECT category, entries FROM category_counts ORDER BY category').df()
        expected = faults.groupby('category').size().rename('entries').reset_index().sort_values('category').reset_index(drop=True)
        pd.testing.assert_frame_equal(expected, categories, check_dtype=False)
        repeats = connection.execute('SELECT * FROM repeated_categories ORDER BY device_id, category').df()
        expected_repeats = faults[faults.device_valid].groupby(['device_id','category']).size().reset_index(name='entries')
        expected_repeats = expected_repeats[expected_repeats.entries > 1].sort_values(['device_id','category']).reset_index(drop=True)
        pd.testing.assert_frame_equal(expected_repeats, repeats, check_dtype=False)
    return {'status':'ok', 'python':sys.executable, 'duckdb':str(database),
            'checked_at':datetime.now(timezone.utc).isoformat(),
            'inputs_fingerprint':inputs_fingerprint(root/'fault_summary_R1.xlsx',files),
            **metrics(faults), 'measurement_files':len(files),
            'measurement_rows':int(files.rows.sum()),
            'note':'Excel-Inhalte, SQL-Views und Dateimetadaten stimmen überein; kein Vollscan der Messwerte.'}

def main():
    try:
        result = check()
    except Exception as exc:
        print(json.dumps({'status':'error','error':str(exc)},ensure_ascii=True,indent=2))
        return 1
    print(json.dumps(result,ensure_ascii=True,indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
