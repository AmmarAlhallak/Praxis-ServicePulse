"""Eigene Berichte reversibel archivieren; Forschungsoriginale und Historie erhalten."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    # Ein Serverdefault ergänzt Bestandszeilen ohne UPDATE und ohne neue Auditeinträge.
    op.add_column(
        "service_reports",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        "only_manual_reports_archived", "service_reports", "NOT archived OR origin = 'manual'"
    )
    op.execute("""CREATE FUNCTION protect_report_archive() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.archived AND NEW.archived THEN
        RAISE EXCEPTION 'Archivierte Berichte sind schreibgeschützt';
      END IF;
      IF NEW.archived IS DISTINCT FROM OLD.archived THEN
        IF NEW.origin <> 'manual' THEN
          RAISE EXCEPTION 'Nur eigene Serviceberichte dürfen archiviert werden';
        END IF;
        IF NEW.version <> OLD.version + 1 THEN
          RAISE EXCEPTION 'Archivierung benötigt eine neue Berichtsversion';
        END IF;
        IF (to_jsonb(NEW) - 'archived' - 'version') IS DISTINCT FROM
           (to_jsonb(OLD) - 'archived' - 'version') THEN
          RAISE EXCEPTION 'Archivstatus und Berichtsinhalte müssen getrennt geändert werden';
        END IF;
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER preserve_archive BEFORE UPDATE ON service_reports
      FOR EACH ROW EXECUTE FUNCTION protect_report_archive()""")


def downgrade():
    raise RuntimeError(
        "Archivstatus und Auditnachweise werden nicht automatisch entfernt. Sicherung verwenden."
    )
