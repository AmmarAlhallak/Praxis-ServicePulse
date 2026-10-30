"""Gezielte Regressionen aus dem Review, ohne Schreiben in den Nutzbestand."""
from pathlib import Path
import io
import pandas as pd
import pytest
from sqlalchemy.exc import OperationalError
from streamlit.testing.v1 import AppTest
from servicepulse import repository as repo
from servicepulse.imports import import_parquet
from servicepulse.measurements import inspect_file

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('function',['reports_frame','files_frame'])
def test_database_outage_is_understandable(monkeypatch,function):
    def unavailable(*args,**kwargs):
        raise OperationalError('test query',{},Exception('isolierte Verbindungsunterbrechung'))
    monkeypatch.setattr(repo,function,unavailable)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('Datenbank ist nicht erreichbar' in error.value for error in app.error)

def test_timezone_aware_upload_requires_explicit_policy(tmp_path):
    frame=pd.DataFrame({'Datetime':pd.date_range('2022-01-01',periods=2,tz='UTC'),'RTD':[-80.,-79.]})
    buffer=io.BytesIO();frame.to_parquet(buffer,index=False)
    with pytest.raises(ValueError,match='Zeitstempel mit Zeitzone'):
        import_parquet(buffer.getvalue(),'123456_temp.parquet',tmp_path)
    assert not list(tmp_path.iterdir())
    file=tmp_path/'123456_temp.parquet';file.write_bytes(buffer.getvalue())
    with pytest.raises(ValueError,match='Zeitstempel mit Zeitzone'):inspect_file(file)

def test_database_configuration_errors_do_not_fall_back(monkeypatch):
    import servicepulse.database as db
    monkeypatch.setattr(db,'load_dotenv',lambda *a,**k:None)
    monkeypatch.delenv('SERVICEPULSE_DATABASE_URL',raising=False)
    db.engine.cache_clear()
    try:
        with pytest.raises(RuntimeError,match='noch nicht eingerichtet'):db.engine()
        monkeypatch.setenv('SERVICEPULSE_DATABASE_URL','sqlite:///not_used.db')
        with pytest.raises(ValueError,match='PostgreSQL'):db.engine()
    finally:db.engine.cache_clear()
