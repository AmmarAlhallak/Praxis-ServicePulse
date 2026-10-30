"""Identische veröffentlichte Dateien als Herkunftsproblem erhalten, nicht verwerfen."""
from alembic import op
revision='0003'
down_revision='0002'

def upgrade():
    op.drop_constraint('measurement_files_sha256_key','measurement_files',type_='unique')
    op.create_index('ix_measurement_files_sha256','measurement_files',['sha256'])

def downgrade():
    raise RuntimeError('Veröffentlichte Herkunftszuordnungen nicht automatisch löschen.')
