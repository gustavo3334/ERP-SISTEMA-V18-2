"""Tabelas do gateway comercial.

Revision ID: 0001_catalog_gateway
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_catalog_gateway"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "commercial_catalog_state",
        sa.Column("key", sa.String(length=120), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "commercial_product_media",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_by", sa.String(length=160)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_commercial_product_media_product_id", "commercial_product_media", ["product_id"])
    op.create_table(
        "commercial_sales_orders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("erp_quote_id", sa.String(length=64)),
        sa.Column("integration_log", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_commercial_sales_orders_code", "commercial_sales_orders", ["code"], unique=True)

def downgrade():
    op.drop_index("ix_commercial_sales_orders_code", "commercial_sales_orders")
    op.drop_table("commercial_sales_orders")
    op.drop_index("ix_commercial_product_media_product_id", "commercial_product_media")
    op.drop_table("commercial_product_media")
    op.drop_table("commercial_catalog_state")
