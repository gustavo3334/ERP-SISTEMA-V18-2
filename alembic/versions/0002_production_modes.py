"""modos de produção do PCP

Revision ID: 0002_production_modes
Revises: 0001_initial
Create Date: 2026-07-21
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_production_modes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _columns("production_orders")
    if "production_mode" not in existing:
        op.add_column(
            "production_orders",
            sa.Column("production_mode", sa.String(length=60), nullable=False, server_default="PRODUZIR_DO_ZERO"),
        )
    if "source_stock_product_id" not in existing:
        op.add_column(
            "production_orders",
            sa.Column("source_stock_product_id", sa.String(length=36), nullable=True),
        )
    if "source_stock_quantity" not in existing:
        op.add_column(
            "production_orders",
            sa.Column("source_stock_quantity", sa.Numeric(14, 3), nullable=False, server_default="0"),
        )
    if "source_stock_cost" not in existing:
        op.add_column(
            "production_orders",
            sa.Column("source_stock_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    existing = _columns("production_orders")
    with op.batch_alter_table("production_orders") as batch_op:
        for column in [
            "source_stock_cost",
            "source_stock_quantity",
            "source_stock_product_id",
            "production_mode",
        ]:
            if column in existing:
                batch_op.drop_column(column)
