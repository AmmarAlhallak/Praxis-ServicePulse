"""Lokale PostgreSQL-Instanz mit vorhandenen Windows-Binärdateien starten."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import os
import secrets
import subprocess
import tempfile
from datetime import datetime
import psycopg
from psycopg import sql
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from alembic import command
from alembic.config import Config
from servicepulse.database import ROOT

PRIVATE=ROOT/'data/private'
STATE=PRIVATE/'postgres.json'
CLUSTER=ROOT/'data/postgresql'

def run(executable,*args,env=None):
    # Windows-Serverprozesse können Pipe-Handles erben. Eine Datei vermeidet,
    # dass communicate() nach beendetem pg_ctl auf den laufenden Server wartet.
    with tempfile.TemporaryFile() as output:
        result=subprocess.run([str(executable),*map(str,args)],stdout=output,stderr=output,stdin=subprocess.DEVNULL,env=env)
    if result.returncode:
        # Programme können Verbindungsparameter ausgeben: keine Geheimnisse weiterreichen.
        raise RuntimeError(f'{Path(executable).name} fehlgeschlagen. Lokales PostgreSQL-Protokoll prüfen.')

def local_settings():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    if not STATE.exists():
        candidates=sorted(Path('C:/Program Files/PostgreSQL').glob('*/bin/pg_ctl.exe'),reverse=True)
        if not candidates:raise RuntimeError('PostgreSQL-Binärdateien fehlen. Installationshinweise: docs/postgresql_windows.md')
        STATE.write_text(json.dumps({'bin':str(candidates[0].parent),'port':55432,'admin_password':secrets.token_urlsafe(32),'app_password':secrets.token_urlsafe(32)}),encoding='utf-8')
        if os.name=='nt':
            # Nur das aktuelle Windows-Konto erhält Zugriff auf lokale Geheimnisse.
            user=subprocess.check_output(['whoami'],text=True).strip()
            run('icacls.exe',PRIVATE,'/inheritance:r','/grant:r',f'{user}:(OI)(CI)F')
    return json.loads(STATE.read_text(encoding='utf-8'))

def connection_url(settings,admin=False,database='servicepulse'):
    return URL.create('postgresql+psycopg',username='servicepulse_owner' if admin else 'servicepulse_app',password=settings['admin_password' if admin else 'app_password'],host='127.0.0.1',port=settings['port'],database=database)

def start_local():
    settings=local_settings();binpath=Path(settings['bin'])
    if not (CLUSTER/'PG_VERSION').exists():
        password_file=PRIVATE/'init-password.tmp'
        password_file.write_text(settings['admin_password'],encoding='utf-8')
        try:run(binpath/'initdb.exe','-D',CLUSTER,'-U','servicepulse_owner','--encoding=UTF8','--locale=C','--auth=scram-sha-256','--pwfile',password_file)
        finally:password_file.unlink(missing_ok=True)
        with (CLUSTER/'postgresql.conf').open('a',encoding='utf-8') as handle:
            handle.write("\nlisten_addresses = '127.0.0.1'\nport = "+str(settings['port'])+"\npassword_encryption = 'scram-sha-256'\n")
    status=subprocess.run([str(binpath/'pg_ctl.exe'),'-D',str(CLUSTER),'status'],capture_output=True)
    if status.returncode:
        run(binpath/'pg_ctl.exe','-D',CLUSTER,'-l',ROOT/'data/postgresql.log','-w','start')
    with psycopg.connect(host='127.0.0.1',port=settings['port'],dbname='postgres',user='servicepulse_owner',password=settings['admin_password'],autocommit=True) as con:
        if not con.execute("SELECT 1 FROM pg_database WHERE datname='servicepulse'").fetchone():
            con.execute('CREATE DATABASE servicepulse OWNER servicepulse_owner')
        if not con.execute("SELECT 1 FROM pg_roles WHERE rolname='servicepulse_app'").fetchone():
            con.execute(sql.SQL('CREATE ROLE servicepulse_app LOGIN PASSWORD {}').format(sql.Literal(settings['app_password'])))
        con.execute('REVOKE ALL ON DATABASE servicepulse FROM PUBLIC')
        con.execute('GRANT CONNECT ON DATABASE servicepulse TO servicepulse_app')
    return settings

def migrate(db):
    cfg=Config(str(ROOT/'alembic.ini'))
    with db.begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(73210646)'))
        cfg.attributes['connection']=connection
        command.upgrade(cfg,'head')

def backup(settings):
    directory=ROOT/'data/backups/postgresql';directory.mkdir(parents=True,exist_ok=True)
    target=directory/f'servicepulse_{datetime.now():%Y%m%d_%H%M%S}.dump'
    env={**os.environ,'PGPASSWORD':settings['admin_password']}
    run(Path(settings['bin'])/'pg_dump.exe','-h','127.0.0.1','-p',settings['port'],'-U','servicepulse_owner','-d','servicepulse','-Fc','-f',target,env=env)
    return target

def prepare():
    settings=start_local();owner=create_engine(connection_url(settings,True),hide_parameters=True)
    migrate(owner)
    with owner.begin() as con:
        con.execute(text('REVOKE CREATE ON SCHEMA public FROM PUBLIC'))
        con.execute(text('GRANT USAGE ON SCHEMA public TO servicepulse_app'))
        con.execute(text('GRANT SELECT, INSERT, UPDATE ON devices,categories,sources,service_reports,service_actions,measurement_files TO servicepulse_app'))
        con.execute(text('GRANT SELECT, INSERT ON audit_log TO servicepulse_app'))
        con.execute(text('GRANT SELECT ON alembic_version TO servicepulse_app'))
        con.execute(text('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO servicepulse_app'))
    from servicepulse.repository import import_research,sync_measurements
    added=import_research(ROOT,owner);files=sync_measurements(ROOT,owner)
    env_path=ROOT/'.env'
    if not env_path.exists():
        env_path.write_text('SERVICEPULSE_DATABASE_URL='+connection_url(settings).render_as_string(hide_password=False)+'\n',encoding='utf-8')
        if os.name=='nt':
            user=subprocess.check_output(['whoami'],text=True).strip()
            run('icacls.exe',env_path,'/inheritance:r','/grant:r',f'{user}:F')
    print(f'PostgreSQL bereit. Neu übernommen: {added} Serviceeinträge, {files} Messdateien.')
    backup(settings)
    owner.dispose()

if __name__=='__main__':
    try:prepare()
    except Exception as exc:
        print('Datenbankstart fehlgeschlagen: '+(str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__+'. Hinweise in docs/postgresql_windows.md.'))
        raise SystemExit(1)
