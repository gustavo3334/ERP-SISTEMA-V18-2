"""backend completo relacional

Revision ID: 0003_backend_completo
Revises: 0002_production_modes
Create Date: 2026-07-27
"""
from alembic import op
from app.database import Base
from app import models_extended  # noqa: F401
revision="0003_backend_completo"
down_revision="0002_production_modes"
branch_labels=None
depends_on=None
EXTENDED_TABLES=["access_profiles","access_profile_permissions","user_access_profiles","audit_logs","stock_balances","stock_movements","purchase_orders","purchase_order_items","sales_orders","sales_order_items","employees","employee_addresses","employee_contacts","employee_health","employee_mei","employee_dependents","employee_alimony","employee_bank_accounts","employee_bonuses","employee_transport_plans","employee_transport_legs","employee_piece_rates","employee_production_entries","employee_payroll_statements","employee_advances","stored_files","employee_document_records","system_settings"]
def upgrade():
    bind=op.get_bind();Base.metadata.create_all(bind=bind,tables=[Base.metadata.tables[n] for n in EXTENDED_TABLES],checkfirst=True)
def downgrade():
    bind=op.get_bind()
    for n in reversed(EXTENDED_TABLES):Base.metadata.tables[n].drop(bind=bind,checkfirst=True)
