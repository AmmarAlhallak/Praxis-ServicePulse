"""Maßnahmen zusammen mit Berichtsversion im Änderungsprotokoll sichern."""
from alembic import op
revision='0002'
down_revision='0001'

def upgrade():
    op.execute('''CREATE OR REPLACE FUNCTION audit_report() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      INSERT INTO audit_log(report_id,version,actor,reason,before,after) VALUES
      (NEW.id,NEW.version,coalesce(nullif(current_setting('servicepulse.actor',true),''),current_user),coalesce(nullif(current_setting('servicepulse.reason',true),''),'Datenbankänderung'),
      CASE WHEN TG_OP='UPDATE' THEN to_jsonb(OLD) || jsonb_build_object('action',coalesce((SELECT text FROM service_actions WHERE report_id=OLD.id),'')) ELSE NULL END,
      to_jsonb(NEW) || jsonb_build_object('action',coalesce(current_setting('servicepulse.action',true),'')));
      RETURN NEW; END $$''')

def downgrade():
    raise RuntimeError('Historie wird nicht automatisch entfernt.')
