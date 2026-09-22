"""Clientes: categoria comercial, pagamentos e tabela de preços individual.

Revision ID: 0007_clientes_precos_pagamentos
Revises: 0006_documentos_persistentes_db
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_clientes_precos_pagamentos"
down_revision = "0006_documentos_persistentes_db"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "clients" in tables:
        cols = _columns(bind, "clients")
        additions = [
            ("legacy_id", sa.String(length=100), True),
            ("address", sa.Text(), True),
            ("status", sa.String(length=50), True),
            ("credit_limit", sa.Numeric(16, 2), True),
            ("preferred_payment", sa.String(length=80), True),
            ("payment_methods_json", sa.JSON(), True),
            ("purchase_history", sa.Text(), True),
            ("front_payload_json", sa.JSON(), True),
        ]
        with op.batch_alter_table("clients") as batch:
            for name, kind, nullable in additions:
                if name not in cols:
                    batch.add_column(sa.Column(name, kind, nullable=nullable))
        # Índices são criados somente quando ainda não existem.
        inspector = sa.inspect(bind)
        indexes = {i["name"] for i in inspector.get_indexes("clients")}
        if "ix_clients_legacy_id" not in indexes:
            op.create_index("ix_clients_legacy_id", "clients", ["legacy_id"], unique=True)
        if "ix_clients_status" not in indexes:
            op.create_index("ix_clients_status", "clients", ["status"], unique=False)
        op.execute("UPDATE clients SET address = '' WHERE address IS NULL")
        op.execute("UPDATE clients SET status = 'Ativo' WHERE status IS NULL")
        op.execute("UPDATE clients SET credit_limit = 0 WHERE credit_limit IS NULL")
        op.execute("UPDATE clients SET preferred_payment = '' WHERE preferred_payment IS NULL")
        op.execute("UPDATE clients SET purchase_history = '' WHERE purchase_history IS NULL")

    inspector = sa.inspect(bind)
    if "client_product_prices" not in set(inspector.get_table_names()):
        op.create_table(
            "client_product_prices",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("client_id", sa.String(length=36), nullable=False),
            sa.Column("product_ref", sa.String(length=120), nullable=False),
            sa.Column("product_name", sa.String(length=220), nullable=False, server_default=""),
            sa.Column("price", sa.Numeric(16, 2), nullable=False, server_default="0"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("client_id", "product_ref", name="uq_client_product_price_ref"),
        )
        op.create_index("ix_client_product_prices_client_id", "client_product_prices", ["client_id"], unique=False)
        op.create_index("ix_client_product_prices_product_ref", "client_product_prices", ["product_ref"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "client_product_prices" in set(inspector.get_table_names()):
        indexes = {i["name"] for i in inspector.get_indexes("client_product_prices")}
        if "ix_client_product_prices_product_ref" in indexes:
            op.drop_index("ix_client_product_prices_product_ref", table_name="client_product_prices")
        if "ix_client_product_prices_client_id" in indexes:
            op.drop_index("ix_client_product_prices_client_id", table_name="client_product_prices")
        op.drop_table("client_product_prices")

    inspector = sa.inspect(bind)
    if "clients" in set(inspector.get_table_names()):
        indexes = {i["name"] for i in inspector.get_indexes("clients")}
        if "ix_clients_status" in indexes:
            op.drop_index("ix_clients_status", table_name="clients")
        if "ix_clients_legacy_id" in indexes:
            op.drop_index("ix_clients_legacy_id", table_name="clients")
        cols = _columns(bind, "clients")
        with op.batch_alter_table("clients") as batch:
            for name in ["front_payload_json", "purchase_history", "payment_methods_json", "preferred_payment", "credit_limit", "status", "address", "legacy_id"]:
                if name in cols:
                    batch.drop_column(name)
