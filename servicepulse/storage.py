"""Kleine relationale Tabellen dauerhaft speichern, Parquet extern belassen."""
from pathlib import Path
import duckdb

def persist(df, files, quality, target):
    Path(target).parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(target)) as con:
        for name, frame in [('faults', df), ('measurement_files', files), ('quality_checks', quality)]:
            con.register('incoming', frame)
            con.execute(f'CREATE OR REPLACE TABLE {name} AS SELECT * FROM incoming')
            con.unregister('incoming')
        con.execute('''CREATE OR REPLACE VIEW category_counts AS
          SELECT category, count(*) AS entries, count(DISTINCT device_id) AS devices
          FROM faults GROUP BY category''')
        con.execute('''CREATE OR REPLACE VIEW repeated_categories AS
          SELECT device_id, category, count(*) AS entries FROM faults
          WHERE device_valid GROUP BY device_id, category HAVING count(*) > 1''')
