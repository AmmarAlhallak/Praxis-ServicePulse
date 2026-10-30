"""Initiales, eingefrorenes Verwaltungsschema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0001'
down_revision=None

def upgrade():
    op.create_table('devices',sa.Column('id',sa.String(6),primary_key=True),sa.Column('name',sa.String(150),nullable=False),sa.Column('model',sa.String(100),nullable=False),sa.Column('location',sa.String(200),nullable=False),sa.CheckConstraint("id ~ '^[0-9]{6}$'",name='device_identifier'))
    op.create_table('categories',sa.Column('id',sa.Integer,primary_key=True),sa.Column('code',sa.String(150),nullable=False,unique=True))
    op.create_table('sources',sa.Column('id',sa.Integer,primary_key=True),sa.Column('kind',sa.String(30),nullable=False),sa.Column('name',sa.Text,nullable=False),sa.Column('sha256',sa.String(64),unique=True),sa.Column('details',JSONB,nullable=False))
    op.create_table('service_reports',sa.Column('id',sa.Integer,primary_key=True),sa.Column('device_id',sa.String(6),sa.ForeignKey('devices.id'),nullable=False),sa.Column('category_id',sa.Integer,sa.ForeignKey('categories.id'),nullable=False),sa.Column('source_id',sa.Integer,sa.ForeignKey('sources.id'),nullable=False),sa.Column('service_date',sa.Date),sa.Column('description',sa.Text,nullable=False),sa.Column('component',sa.Text,nullable=False),sa.Column('status',sa.String(30),nullable=False),sa.Column('notes',sa.Text,nullable=False),sa.Column('origin',sa.String(20),nullable=False),sa.Column('source_sheet',sa.Text),sa.Column('source_row',sa.Integer),sa.Column('original',JSONB),sa.Column('import_key',sa.String(200),nullable=False,unique=True),sa.Column('version',sa.Integer,nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.CheckConstraint("origin IN ('research','manual')",name='report_origin'),sa.CheckConstraint("status IN ('offen','in Bearbeitung','abgeschlossen','nicht angegeben')",name='report_status'),sa.CheckConstraint("origin <> 'research' OR (original IS NOT NULL AND source_row IS NOT NULL AND source_sheet IS NOT NULL)",name='historical_provenance'))
    op.create_index('ix_service_reports_device_id','service_reports',['device_id'])
    op.create_index('ix_service_reports_service_date','service_reports',['service_date'])
    op.create_table('service_actions',sa.Column('id',sa.Integer,primary_key=True),sa.Column('report_id',sa.Integer,sa.ForeignKey('service_reports.id'),nullable=False,unique=True),sa.Column('text',sa.Text,nullable=False))
    op.create_table('measurement_files',sa.Column('id',sa.Integer,primary_key=True),sa.Column('device_id',sa.String(6),sa.ForeignKey('devices.id'),nullable=False),sa.Column('source_id',sa.Integer,sa.ForeignKey('sources.id'),nullable=False),sa.Column('path',sa.Text,nullable=False,unique=True),sa.Column('sha256',sa.String(64),nullable=False,unique=True),sa.Column('kind',sa.String(10),nullable=False),sa.Column('model',sa.Text,nullable=False),sa.Column('rows',sa.BigInteger,nullable=False),sa.Column('columns',sa.Text,nullable=False),sa.Column('first_time',sa.DateTime),sa.Column('last_time',sa.DateTime),sa.Column('size_bytes',sa.BigInteger,nullable=False),sa.Column('mtime_ns',sa.BigInteger,nullable=False),sa.CheckConstraint("kind IN ('temp','events')",name='file_kind'))
    op.create_index('ix_measurement_files_device_id','measurement_files',['device_id'])
    op.create_table('audit_log',sa.Column('id',sa.Integer,primary_key=True),sa.Column('report_id',sa.Integer,sa.ForeignKey('service_reports.id'),nullable=False),sa.Column('version',sa.Integer,nullable=False),sa.Column('actor',sa.Text,nullable=False),sa.Column('reason',sa.Text,nullable=False),sa.Column('before',JSONB),sa.Column('after',JSONB,nullable=False),sa.Column('changed_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.UniqueConstraint('report_id','version'))
    op.create_index('ix_audit_log_report_id','audit_log',['report_id'])
    op.execute('''CREATE FUNCTION protect_research() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Serviceberichte dürfen nicht gelöscht werden'; END IF;
      IF NEW.original IS DISTINCT FROM OLD.original OR NEW.origin IS DISTINCT FROM OLD.origin OR NEW.import_key IS DISTINCT FROM OLD.import_key OR NEW.source_sheet IS DISTINCT FROM OLD.source_sheet OR NEW.source_row IS DISTINCT FROM OLD.source_row OR NEW.source_id IS DISTINCT FROM OLD.source_id THEN
        RAISE EXCEPTION 'Originalherkunft ist unveränderlich'; END IF; RETURN NEW; END $$''')
    op.execute('CREATE TRIGGER preserve_reports BEFORE UPDATE OR DELETE ON service_reports FOR EACH ROW EXECUTE FUNCTION protect_research()')
    op.execute('''CREATE FUNCTION audit_report() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      INSERT INTO audit_log(report_id,version,actor,reason,before,after) VALUES (NEW.id,NEW.version,coalesce(nullif(current_setting('servicepulse.actor',true),''),current_user),coalesce(nullif(current_setting('servicepulse.reason',true),''),'Datenbankänderung'),CASE WHEN TG_OP='UPDATE' THEN to_jsonb(OLD) ELSE NULL END,to_jsonb(NEW)); RETURN NEW; END $$''')
    op.execute('CREATE TRIGGER audit_reports AFTER INSERT OR UPDATE ON service_reports FOR EACH ROW EXECUTE FUNCTION audit_report()')

def downgrade():
    raise RuntimeError('Kein automatisches Löschen von Servicehistorie. Sicherung wiederherstellen.')
