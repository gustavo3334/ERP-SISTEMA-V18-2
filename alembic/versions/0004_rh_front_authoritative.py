"""RH authoritative frontend hydration

Revision ID: 0004_rh_front_authoritative
Revises: 0003_backend_completo
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_rh_front_authoritative"
down_revision = "0003_backend_completo"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("employees")}


def upgrade() -> None:
    columns = _columns()
    if "employee_type" not in columns:
        op.add_column("employees", sa.Column("employee_type", sa.String(length=60), nullable=True))
    if "front_payload_json" not in columns:
        op.add_column("employees", sa.Column("front_payload_json", sa.JSON(), nullable=True))
    op.execute("UPDATE employees SET employee_type = 'Operacional' WHERE employee_type IS NULL")
    op.execute("UPDATE employees SET front_payload_json = '{}' WHERE front_payload_json IS NULL")


def downgrade() -> None:
    columns = _columns()
    if "front_payload_json" in columns:
        op.drop_column("employees", "front_payload_json")
    if "employee_type" in columns:
        op.drop_column("employees", "employee_type")
