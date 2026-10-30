"""Echtes PostgreSQL, getrennte kurzlebige Testdatenbank. Keine Testberichte im Nutzbestand."""
from pathlib import Path
from datetime import date
import uuid
import json
import pandas as pd
import pytest
import psycopg
from psycopg import sql
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError
from servicepulse import repository as repo
from servicepulse.models import Source,MeasurementFile
from servicepulse.faults import read_faults,metrics
from scripts.prepare_database import local_settings,connection_url,migrate

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def isolated_database():
    settings=local_settings();name='servicepulse_test_'+uuid.uuid4().hex
    args=dict(host='127.0.0.1',port=settings['port'],dbname='postgres',user='servicepulse_owner',password=settings['admin_password'],autocommit=True)
    with psycopg.connect(**args) as connection:connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    db=create_engine(connection_url(settings,True,database=name),hide_parameters=True)
    try:
        migrate(db);yield db
    finally:
        db.dispose()
        with psycopg.connect(**args) as connection:connection.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

@pytest.fixture
def database(isolated_database):
    db=isolated_database
    # Ausschließlich die oben erzeugte Testdatenbank. Originaldatenbank nie leeren.
    assert db.url.database.startswith('servicepulse_test_')
    with db.begin() as con:con.execute(text('TRUNCATE audit_log,service_actions,service_reports,measurement_files,sources,categories,devices RESTART IDENTITY CASCADE'))
    repo.import_research(ROOT,db)
    return db

def data(**changes):
    return dict(device_id='806279',service_date=date(2026,10,30),category='Unbekannt',description='Künstlicher Bericht ausschließlich in der Testdatenbank',component='',action='Testmaßnahme',status='offen',notes='',source='Automatisierter Test',actor='pytest',reason='Testanlage',**changes)

def test_import_idempotent_and_original_values(database):
    assert repo.import_research(ROOT,database)==0
    original=read_faults(ROOT/'fault_summary_R1.xlsx')
    actual=repo.reports_frame(database,originals=True)
    pd.testing.assert_frame_equal(original,actual[original.columns],check_dtype=False)
    assert list(metrics(repo.reports_frame(database)).values())[:4]==[46,24,11,5]
    with Session(database) as session:
        from servicepulse.models import Audit
        assert len(session.scalars(select(Audit)).all())==46

def test_create_edit_durable_and_audited(database):
    values=data();rid=repo.save_report(values,request_key='same-submission',db=database)
    assert repo.save_report(values,request_key='same-submission',db=database)==rid
    database.dispose() # Neue Verbindung, keine Prozess-/Session-Speicherung.
    assert len(repo.reports_frame(database))==47
    values.update(description='Geänderte Testbeschreibung',action='Zweite Testmaßnahme',status='abgeschlossen',reason='Testkorrektur')
    repo.save_report(values,rid,1,db=database)
    updated=repo.reports_frame(database).query('report_id==@rid').iloc[0]
    assert updated.action=='Zweite Testmaßnahme' and updated.report_version==2
    log=repo.history(rid,database)
    assert len(log)==2 and log[-1]['Vorher']['action']=='Testmaßnahme' and log[-1]['Nachher']['action']=='Zweite Testmaßnahme'
    with pytest.raises(ValueError,match='inzwischen geändert'):repo.save_report(values,rid,1,db=database)

def test_historical_edits_keep_originals_and_no_delete(database):
    original=repo.reports_frame(database,True)
    current=repo.reports_frame(database).iloc[0]
    values=data();values.update(device_id=current.device_id,category=current.category,description='Arbeitsfassung im Test',source=current.source_file)
    repo.save_report(values,int(current.report_id),1,db=database)
    pd.testing.assert_frame_equal(original,repo.reports_frame(database,True))
    with pytest.raises(DBAPIError):
        with database.begin() as con:con.execute(text('DELETE FROM service_reports WHERE id=:id'),{'id':int(current.report_id)})
    with pytest.raises(DBAPIError):
        with database.begin() as con:con.execute(text("UPDATE service_reports SET original='{}'::jsonb WHERE id=:id"),{'id':int(current.report_id)})

def test_new_device_missing_fields_and_validation(database):
    repo.add_device('999991','Testgerät ohne Sensoren',db=database)
    values=data();values.update(device_id='999991',service_date=None,description='',action='')
    rid=repo.save_report(values,db=database)
    row=repo.reports_frame(database).query('report_id==@rid').iloc[0]
    assert pd.isna(row.event_date) and row.origin=='manual' and row.category=='Unbekannt'
    assert repo.files_frame(database).empty
    with pytest.raises(ValueError,match='bereits registriert'):repo.add_device('999991',db=database)
    with pytest.raises(ValueError):repo.add_device('../bad',db=database)
    values['source']=''
    with pytest.raises(ValueError,match='Herkunft'):repo.save_report(values,db=database)
    assert len(repo.reports_frame(database))==47

def test_management_form_updates_statistics_and_history(database,monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(repo,'engine',lambda:database)
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
    assert not app.exception and app.metric[0].value=='46'
    description=next(w for w in app.text_area if w.label=='Beschreibung der Störung')
    source=next(w for w in app.text_input if w.label=='Quelle / Herkunft')
    description.set_value('Automatischer Formulartest, kein Forschungsbefund');source.set_value('Isolierte PostgreSQL-Testdatenbank')
    next(b for b in app.button if b.label=='Servicebericht speichern').click().run()
    assert not app.exception and not app.error
    assert app.metric[0].value=='47'
    assert any('dauerhaft gespeichert' in v.value for v in app.success)
    assert len(repo.reports_frame(database))==47
    app.radio(key='report_mode').set_value('Bestehenden Bericht bearbeiten').run()
    assert not app.exception
    latest=int(repo.reports_frame(database).report_id.max())
    app.selectbox(key='edit_report_806279').set_value(latest).run()
    next(w for w in app.text_area if w.label=='Reparatur oder Wartungsmaßnahme (optional)').set_value('Teständerung aus Formular')
    next(w for w in app.text_input if w.label=='Grund der Änderung').set_value('Formularbearbeitung prüfen')
    next(b for b in app.button if b.label=='Änderungen speichern').click().run()
    assert not app.exception and not app.error
    assert repo.history(latest,database)[-1]['Nachher']['action']=='Teständerung aus Formular'

def test_parquet_import_validates_null_times_and_duplicate_bytes(tmp_path,database):
    import io
    from servicepulse.imports import import_parquet
    frame=pd.DataFrame({'Datetime':pd.to_datetime(['2022-01-01',None]),'RTD':[-80.,-79.]})
    buffer=io.BytesIO();frame.to_parquet(buffer,index=False)
    with pytest.raises(ValueError,match='fehlende Zeitstempel'):import_parquet(buffer.getvalue(),'999991_temp.parquet',tmp_path)
    frame=frame.dropna();frame.to_parquet(tmp_path/'999991_temp.parquet',index=False)
    repo.register_file(tmp_path/'999991_temp.parquet','Test',database)
    with pytest.raises(ValueError,match='Identische Messdatei'):import_parquet((tmp_path/'999991_temp.parquet').read_bytes(),'999992_temp.parquet',tmp_path,registry=repo.files_frame(database),source='Test')
    assert not (tmp_path/'999992_temp.parquet').exists()

def test_owned_postgresql_restart_keeps_new_report(database):
    from scripts.prepare_database import start_local,run,CLUSTER
    settings=local_settings();rid=repo.save_report(data(),db=database)
    database.dispose();repo.engine().dispose()
    try:
        run(Path(settings['bin'])/'pg_ctl.exe','-D',CLUSTER,'-m','fast','-w','stop')
    finally:
        start_local()
    persisted=repo.reports_frame(database)
    row=persisted.loc[persisted.report_id.eq(rid)].iloc[0]
    assert row.fault_text=='Künstlicher Bericht ausschließlich in der Testdatenbank'
    assert len(repo.history(rid,database))==1

def test_application_role_can_save_but_cannot_delete_or_rewrite_audit(database):
    settings=local_settings()
    with database.begin() as con:
        con.execute(text('GRANT USAGE ON SCHEMA public TO servicepulse_app'))
        con.execute(text('GRANT SELECT, INSERT, UPDATE ON devices,categories,sources,service_reports,service_actions,measurement_files TO servicepulse_app'))
        con.execute(text('GRANT SELECT, INSERT ON audit_log TO servicepulse_app'))
        con.execute(text('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO servicepulse_app'))
    app=create_engine(connection_url(settings,database=database.url.database),hide_parameters=True)
    try:
        rid=repo.save_report(data(),db=app)
        assert len(repo.history(rid,app))==1
        with pytest.raises(DBAPIError):
            with app.begin() as con:con.execute(text('DELETE FROM service_reports WHERE id=:id'),{'id':rid})
        with pytest.raises(DBAPIError):
            with app.begin() as con:con.execute(text("UPDATE audit_log SET reason='tampered' WHERE report_id=:id"),{'id':rid})
    finally:app.dispose()

def test_dump_restore_retains_report_and_audit(database,tmp_path):
    import os
    from scripts.prepare_database import run
    settings=local_settings();rid=repo.save_report(data(),db=database)
    target=tmp_path/'isolated_test.dump';env={**os.environ,'PGPASSWORD':settings['admin_password']}
    run(Path(settings['bin'])/'pg_dump.exe','-h','127.0.0.1','-p',settings['port'],'-U','servicepulse_owner','-d',database.url.database,'-Fc','-f',target,env=env)
    name='servicepulse_restore_test_'+uuid.uuid4().hex
    args=dict(host='127.0.0.1',port=settings['port'],dbname='postgres',user='servicepulse_owner',password=settings['admin_password'],autocommit=True)
    with psycopg.connect(**args) as c:c.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    restored=create_engine(connection_url(settings,True,database=name),hide_parameters=True)
    try:
        run(Path(settings['bin'])/'pg_restore.exe','-h','127.0.0.1','-p',settings['port'],'-U','servicepulse_owner','-d',name,'--exit-on-error',target,env=env)
        assert len(repo.reports_frame(restored))==47
        assert len(repo.history(rid,restored))==1
        assert len(repo.reports_frame(restored,True))==46
    finally:
        restored.dispose()
        with psycopg.connect(**args) as c:c.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

def test_real_temperature_gap_warm_values_and_corrected_events():
    from servicepulse.case_review import review_temperature
    from servicepulse.measurements import offsets,event_window
    path=ROOT/'data/raw/Revco/806279_temp.parquet'
    if not path.exists():pytest.skip('Reale Parquet-Datei fehlt')
    gaps,daily,warm,states=review_temperature(path,'2022-06-21','2022-07-06')
    assert gaps.iloc[0].seconds==432715
    assert gaps.iloc[0].previous==pd.Timestamp('2022-06-22 10:36:20')
    assert warm.rows==145 and warm.maximum==pytest.approx(21.8)
    assert daily.repeated_timestamps.sum()==0
    clock=offsets(ROOT/'research/reference/data/raw_data/other_data/time_offsets.csv')['806279']
    assert clock==pd.Timedelta(minutes=9,seconds=20)
    events=event_window(ROOT/'data/raw/Revco/806279_events.parquet','2022-06-21','2022-07-06',clock)
    assert events.loc[events.Event.eq('Shutdown'),'Datetime'].iloc[0]==pd.Timestamp('2022-06-22 10:36:52')
    assert events.loc[events.Event.eq('Display Power On'),'Datetime'].iloc[0]==pd.Timestamp('2022-06-27 10:48:09')
