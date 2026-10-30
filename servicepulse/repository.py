"""Transaktionaler PostgreSQL-Zugriff und nachvollziehbarer Erstimport."""
from pathlib import Path
from datetime import date
import hashlib
import json
import re
import uuid
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from servicepulse.database import engine
from servicepulse.models import Device, Category, Source, Report, Action, MeasurementFile, Audit
from servicepulse.faults import read_faults
from servicepulse.measurements import inventory, time_bounds

STATUSES=['offen','in Bearbeitung','abgeschlossen','nicht angegeben']

def digest_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()

def category(session,code):
    result=session.scalar(select(Category).where(Category.code==code))
    if result is None:
        result=Category(code=code);session.add(result);session.flush()
    return result

def context(session,actor,reason,action=''):
    for key,value in [('actor',actor),('reason',reason),('action',action)]:
        session.execute(text("SELECT set_config(:key,:value,true)"),{'key':'servicepulse.'+key,'value':value})

def import_research(root,db=None):
    """Einmaliger Import pro Excel-Quellzeile; ein geänderter Quellbestand wird abgewiesen."""
    root=Path(root);source=root/'fault_summary_R1.xlsx';sha=digest_file(source)
    df=read_faults(source)
    with Session(db or engine()) as session, session.begin():
        session.execute(text('SELECT pg_advisory_xact_lock(73210646)'))
        context(session,'Erstimport','Unveränderte wissenschaftliche Excel-Referenz')
        origin=session.scalar(select(Source).where(Source.kind=='research_excel'))
        if origin is not None and origin.sha256!=sha:
            raise ValueError('Die Excel-Referenz wurde verändert. Kein erneuter automatischer Import erlaubt.')
        if origin is None:
            origin=Source(kind='research_excel',name=source.name,sha256=sha,details={'article':'10.1038/s41597-023-02808-6','license':'CC0 laut Figshare','sheet':str(df.source_sheet.iloc[0])})
            session.add(origin);session.flush()
        added=0
        # to_json sichert auch die Quellspalten; keine Rundung/Umdeutung ihrer Inhalte.
        originals=json.loads(df.to_json(orient='records',date_format='iso',double_precision=15))
        for (_,row),original in zip(df.iterrows(),originals):
            key=f'{sha}:{row.source_sheet}:{row.source_row}'
            if session.scalar(select(Report.id).where(Report.import_key==key)) is not None:continue
            if session.get(Device,row.device_id) is None:session.add(Device(id=row.device_id,name='',model='',location=''))
            cat=category(session,row.category)
            session.add(Report(device_id=row.device_id,category_id=cat.id,source_id=origin.id,
                service_date=None if pd.isna(row.event_date) else row.event_date.date(),description='' if pd.isna(row.fault_text) else row.fault_text,
                component='',status='nicht angegeben',notes='',origin='research',source_sheet=row.source_sheet,source_row=int(row.source_row),original=original,import_key=key))
            added+=1
        category(session,'Unbekannt')
    return added

def register_file(path,source_name,db=None,research=False):
    from servicepulse.measurements import inspect_file
    path=Path(path).resolve();meta=inspect_file(path);sha=digest_file(path)
    first,last=time_bounds(path)
    if (first is None or last is None) and not research:raise ValueError('Die Messdatei enthält keine gültigen Zeitstempel.')
    with Session(db or engine()) as session,session.begin():
        session.execute(text('SELECT pg_advisory_xact_lock(73210646)'))
        existing=session.scalar(select(MeasurementFile).where(MeasurementFile.path==str(path)))
        if existing:
            if existing.sha256!=sha:raise ValueError('Eine bereits registrierte Messdatei wurde verändert.')
            return False
        if not research and session.scalar(select(MeasurementFile.id).where(MeasurementFile.sha256==sha)):
            raise ValueError('Identische Messdatei ist bereits registriert, auch wenn der Name anders ist.')
        if session.get(Device,meta['device_id']) is None:
            session.add(Device(id=meta['device_id'],name='',model=meta['model'],location=''));session.flush()
        origin=Source(kind='measurement',name=source_name,sha256=None,details={'file_sha256':sha})
        session.add(origin);session.flush()
        stat=path.stat()
        session.add(MeasurementFile(**meta,source_id=origin.id,sha256=sha,first_time=first,last_time=last,size_bytes=stat.st_size,mtime_ns=stat.st_mtime_ns))
    return True

def sync_measurements(root,db=None):
    files,errors=inventory(Path(root)/'data/raw')
    if errors:raise ValueError('Nicht lesbare Messdateien vorhanden. Qualitätsbericht prüfen.')
    added=0
    with Session(db or engine()) as s:
        registered={r.path:r for r in s.scalars(select(MeasurementFile))}
    with Session(db or engine()) as s,s.begin():
        for identifier,group in files.groupby('device_id'):
            models=set(group.model)&{'Revco','Haier'}
            device=s.get(Device,identifier)
            if device is not None and not device.model and len(models)==1:
                device.model=next(iter(models))
    for path in files.path:
        old=registered.get(path);stat=Path(path).stat()
        if old and (old.size_bytes,old.mtime_ns)==(stat.st_size,stat.st_mtime_ns):continue
        added+=int(register_file(path,'Veröffentlichte Forschungsdaten; siehe Herkunftsdokumentation',db,research=True))
    return added

def reports_frame(db=None,originals=False):
    with Session(db or engine()) as session:
        rows=session.execute(select(Report,Category.code,Source.name).join(Category,Report.category_id==Category.id).join(Source,Report.source_id==Source.id).order_by(Report.id)).all()
        actions={r.report_id:r.text for r in session.scalars(select(Action))}
        records=[]
        for report,code,source_name in rows:
            if originals:
                if report.origin=='research':records.append(report.original)
                continue
            row=dict(report.original or {})
            row.update(device_id=report.device_id,event_date=report.service_date,category=code,fault_text=report.description,
                report_id=report.id,report_version=report.version,origin=report.origin,status=report.status,component=report.component,
                action=actions.get(report.id,''),notes=report.notes,source_file=source_name,source_sheet=report.source_sheet,source_row=report.source_row)
            if report.origin=='manual':
                row.update(freezer_id=report.device_id,registered_date=report.service_date,main_fault=report.description,
                           category_raw=code,**{'Fault categories':code})
            row.update(device_valid=True,category_group=re.sub(r'\s*\(No fix\)$','',code),no_fix='(No fix)' in code,duplicate=False,date_precision='day')
            records.append(row)
    frame=pd.DataFrame(records)
    if frame.empty:
        frame=pd.DataFrame(columns=['device_id','event_date','category','fault_text','device_valid','category_group','no_fix','duplicate','date_precision','source_row','source_sheet','source_file','report_id','origin','category_raw','freezer_id','registered_date','main_fault','Fault categories'])
    for col in ['event_date','registered_date']:
        if col in frame:frame[col]=pd.to_datetime(frame[col],format='ISO8601',errors='coerce')
    return frame

def files_frame(db=None):
    with Session(db or engine()) as session:
        rows=session.scalars(select(MeasurementFile).order_by(MeasurementFile.path)).all()
        return pd.DataFrame([{key:getattr(r,key) for key in ['path','device_id','kind','model','rows','columns']} for r in rows],columns=['path','device_id','kind','model','rows','columns'])

def file_digests(db=None):
    with Session(db or engine()) as session:
        return pd.DataFrame([{'path':r.path,'sha256':r.sha256} for r in session.scalars(select(MeasurementFile))],columns=['path','sha256'])

def devices_frame(db=None):
    with Session(db or engine()) as session:
        return pd.DataFrame([{'Geräte-ID':r.id,'Bezeichnung':r.name,'Modell':r.model,'Standort':r.location} for r in session.scalars(select(Device).order_by(Device.id))],columns=['Geräte-ID','Bezeichnung','Modell','Standort'])

def add_device(identifier,name='',model='',location='',db=None):
    if not re.fullmatch(r'\d{6}',identifier):raise ValueError('Bitte eine eindeutige sechsstellige Geräte-ID eingeben.')
    if len(name)>150 or len(model)>100 or len(location)>200:raise ValueError('Geräteangaben sind zu lang.')
    try:
        with Session(db or engine()) as session,session.begin():
            session.add(Device(id=identifier,name=name.strip(),model=model.strip(),location=location.strip()))
    except IntegrityError as exc:raise ValueError('Diese Geräte-ID ist bereits registriert.') from exc

def save_report(data,report_id=None,expected_version=None,request_key=None,db=None):
    """Eine Transaktion für Bericht, Maßnahme und Audit; optimistischer Änderungsschutz."""
    if data.get('status') not in STATUSES:raise ValueError('Bitte einen gültigen Status wählen.')
    if not str(data.get('source','')).strip():raise ValueError('Bitte die Herkunft angeben, gegebenenfalls „Nicht bekannt“.')
    if not str(data.get('reason','')).strip():raise ValueError('Bitte den Grund der Änderung angeben.')
    day=data.get('service_date')
    if day is not None and not isinstance(day,date):raise ValueError('Ungültiges Servicedatum.')
    try:
        with Session(db or engine()) as session,session.begin():
            session.execute(text('SELECT pg_advisory_xact_lock(73210646)'))
            if session.get(Device,data['device_id']) is None:raise ValueError('Gerät bitte zuerst anlegen.')
            context(session,data.get('actor') or 'Lokale Bedienung',data['reason'],data.get('action',''))
            category_id=category(session,data.get('category') or 'Unbekannt').id
            if report_id is None:
                key='manual:'+str(request_key or uuid.uuid4())
                existing=session.scalar(select(Report).where(Report.import_key==key))
                if existing:return existing.id
                origin=Source(kind='manual',name=data['source'].strip(),details={'entered_locally':True})
                session.add(origin);session.flush()
                report=Report(device_id=data['device_id'],source_id=origin.id,origin='manual',import_key=key)
                session.add(report)
            else:
                report=session.get(Report,int(report_id))
                if report is None:raise ValueError('Bericht wurde nicht gefunden.')
                if report.version!=expected_version:raise ValueError('Der Bericht wurde inzwischen geändert. Bitte neu laden, bevor du erneut speicherst.')
                if report.device_id!=data['device_id']:raise ValueError('Die Gerätezuordnung bestehender Berichte bleibt erhalten.')
                # Auch reine Maßnahmen-/Bemerkungsänderungen erhöhen die Version.
                report.version+=1
            report.category_id=category_id
            report.service_date=day;report.description=data.get('description','').strip()
            report.component=data.get('component','').strip();report.status=data['status'];report.notes=data.get('notes','').strip()
            session.flush()
            action=session.scalar(select(Action).where(Action.report_id==report.id))
            if action is None:session.add(Action(report_id=report.id,text=data.get('action','').strip()))
            else:action.text=data.get('action','').strip()
            result=report.id
        return result
    except StaleDataError as exc:raise ValueError('Gleichzeitige Änderung erkannt. Bitte neu laden.') from exc

def history(report_id,db=None):
    with Session(db or engine()) as session:
        return [{'Version':r.version,'Zeitpunkt':r.changed_at,'Bearbeiter':r.actor,'Grund':r.reason,'Vorher':r.before,'Nachher':r.after}
                for r in session.scalars(select(Audit).where(Audit.report_id==int(report_id)).order_by(Audit.version))]
