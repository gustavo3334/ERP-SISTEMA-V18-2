"""Persistência universal com revisões e proteção contra sobrescrita concorrente.

Revision ID: 0005_persistencia_universal_revisions
Revises: 0004_rh_front_authoritative
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_state_revisions"
down_revision = "0004_rh_front_authoritative"
branch_labels = None
depends_on = None


def _columns(bind, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # A migração inicial deste projeto usa metadata.create_all. Em instalações
    # totalmente novas, ela já pode criar a coluna/tabela desta revisão. Por isso
    # esta migration precisa ser segura tanto para bancos existentes quanto novos.
    if "front_states" in tables and "revision" not in _columns(bind, "front_states"):
        with op.batch_alter_table("front_states") as batch:
            batch.add_column(
                sa.Column("revision", sa.Integer(), nullable=False, server_default="0")
            )
        op.execute("UPDATE front_states SET revision = 1 WHERE revision = 0")

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "front_state_revisions" not in tables:
        op.create_table(
            "front_state_revisions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("state_key", sa.String(length=120), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("state_key", "revision", name="uq_front_state_revision"),
        )
        op.create_index(
            "ix_front_state_revisions_state_key",
            "front_state_revisions",
            ["state_key"],
            unique=False,
        )
        op.create_index(
            "ix_front_state_revisions_revision",
            "front_state_revisions",
            ["revision"],
            unique=False,
        )
        op.create_index(
            "ix_front_state_revisions_created_at",
            "front_state_revisions",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "front_state_revisions" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("front_state_revisions")}
        if "ix_front_state_revisions_created_at" in indexes:
            op.drop_index("ix_front_state_revisions_created_at", table_name="front_state_revisions")
        if "ix_front_state_revisions_revision" in indexes:
            op.drop_index("ix_front_state_revisions_revision", table_name="front_state_revisions")
        if "ix_front_state_revisions_state_key" in indexes:
            op.drop_index("ix_front_state_revisions_state_key", table_name="front_state_revisions")
        op.drop_table("front_state_revisions")

    inspector = sa.inspect(bind)
    if "front_states" in set(inspector.get_table_names()) and "revision" in _columns(bind, "front_states"):
        with op.batch_alter_table("front_states") as batch:
            batch.drop_column("revision")
