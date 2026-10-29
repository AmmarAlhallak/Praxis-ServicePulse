import pandas as pd
import pytest
from servicepulse.measurements import inspect_file, inventory, series_window, window_comparison, event_window, audit_file
from servicepulse.storage import persist
from servicepulse.faults import read_faults, quality
from pathlib import Path
import duckdb

@pytest.fixture
def sample(tmp_path):
    # Sichtbar synthetische Testfixture, ausschließlich in pytest-Tempverzeichnis.
    path=tmp_path/'123456_temp.parquet'
    pd.DataFrame({'Datetime':pd.to_datetime(['2020-01-01 01:00','2020-01-01 02:00','2020-01-02 12:00','2020-01-03 01:00']),
                  'RTD':[-80.,-78.,20.,-82.]}).to_parquet(path,index=False)
    return path

def test_metadata_and_aggregates(sample):
    assert inspect_file(sample)['rows'] == 4
    df=series_window(sample,'RTD','2020-01-01','2020-01-04','day')
    assert df['mean'].tolist()==[-79.,20.,-82.]
    comparison=window_comparison(sample,'RTD','2020-01-02',1)
    assert comparison['mean'].tolist()==[-79.,-82.]
    assert comparison['valid'].tolist()==[2,1]
    assert series_window(sample,'RTD','2030-01-01','2030-01-02').empty
    with pytest.raises(ValueError):series_window(sample,'RTD"; DROP TABLE x;--','2020-01-01','2020-01-02')

def test_event_clock_shift_and_audit(sample):
    shifted=event_window(sample,'2020-01-01 02:00','2020-01-01 03:00',pd.Timedelta(hours=1))
    assert shifted.Datetime.item()==pd.Timestamp('2020-01-01 02:00')
    assert audit_file(sample)['repeated_timestamps']==0

def test_bad_parquet_is_reported(tmp_path):
    (tmp_path/'123456_temp.parquet').write_text('not parquet')
    files,errors=inventory(tmp_path)
    assert files.empty and len(errors)==1

def test_import_schema_requires_timestamps_and_measurement(tmp_path):
    path=tmp_path/'123456_temp.parquet'
    pd.DataFrame({'Datetime':['2020-01-01'],'RTD':[-80.]}).to_parquet(path,index=False)
    with pytest.raises(ValueError,match='Zeitstempel'):inspect_file(path)
    pd.DataFrame({'Datetime':pd.to_datetime(['2020-01-01'])}).to_parquet(path,index=False)
    with pytest.raises(ValueError,match='numerische'):inspect_file(path)

def test_duckdb_storage_with_empty_inventory(tmp_path):
    df=read_faults(Path(__file__).resolve().parents[1]/'fault_summary_R1.xlsx')
    files,_=inventory(tmp_path)
    dest=tmp_path/'test.duckdb'
    persist(df,files,quality(df),dest)
    with duckdb.connect(str(dest)) as con:
        assert con.execute('SELECT sum(entries) FROM category_counts').fetchone()[0]==46
        assert con.execute('SELECT count(*) FROM repeated_categories').fetchone()[0]==5
