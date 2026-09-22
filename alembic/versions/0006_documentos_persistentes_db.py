"""Guarda cópia binária dos documentos no banco para sobreviver ao filesystem efêmero.

Revision ID: 0006_documentos_persistentes_db
Revises: 0005_persistencia_universal_revisions
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_documentos_persistentes_db"
down_revision = "0005_state_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "stored_files" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("stored_files")}
    if "content_blob" not in columns:
        with op.batch_alter_table("stored_files") as batch:
            batch.add_column(sa.Column("content_blob", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "stored_files" not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns("stored_files")}
    if "content_blob" in columns:
        with op.batch_alter_table("stored_files") as batch:
            batch.drop_column("content_blob")
