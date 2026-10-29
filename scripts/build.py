"""Reproduzierbare lokale Aufbereitung und Qualitätsbericht."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import hashlib
import pandas as pd
from servicepulse.faults import read_faults, metrics, quality, compare_reference, category_control
from servicepulse.measurements import inventory, audit_file
from servicepulse.storage import persist

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT/'fault_summary_R1.xlsx'
    df = read_faults(source)
    files, errors = inventory(ROOT/'data/raw')
    output = ROOT/'data/processed';output.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output/'faults.parquet', index=False)
    quality(df).to_csv(output/'fault_quality.csv', index=False)
    category_control(source,df).to_csv(output/'category_control.csv',index=False)
    files.to_csv(output/'measurement_files.csv', index=False)
    persist(df, files, quality(df), output/'servicepulse.duckdb')
    audits = []
    for i, path in enumerate(files.path):
        try:
            audits.append(audit_file(path))
        except Exception as exc:
            errors.append({'path':path, 'error':str(exc)})
        print(f'Prüfung {i+1}/{len(files)}', flush=True)
    pd.DataFrame(audits).to_csv(output/'measurement_quality.csv', index=False)
    (output/'errors.json').write_text(json.dumps(errors,indent=2), encoding='utf-8')
    stats = metrics(df)
    stats['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    stats['measurement_files'] = len(files)
    stats['measurement_rows'] = int(files.rows.sum())
    (output/'summary.json').write_text(json.dumps(stats,indent=2), encoding='utf-8')
    reference = ROOT/'research/reference/data/raw_data/other_data/freezer_faults.csv'
    if reference.exists():
        compare_reference(df, reference).to_csv(output/'source_comparison.csv', index=False)
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
