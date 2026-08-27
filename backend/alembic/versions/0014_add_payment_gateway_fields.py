"""Add razorpay and gateway metadata fields to payments table.

Revision ID: 0014_payment_gateway_fields
Revises: 0013_add_voice_calls_table
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.db.base import JSON_TYPE

# revision identifiers, used by Alembic.
revision: str = '0014_payment_gateway_fields'
down_revision: Union[str, None] = '0013_add_voice_calls_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely add extended gateway fields to payments table
    op.add_column('payments', sa.Column('razorpay_payment_id', sa.String(length=255), nullable=True))
    op.add_column('payments', sa.Column('razorpay_order_id', sa.String(length=255), nullable=True))
    op.add_column('payments', sa.Column('bank', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('wallet', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('vpa', sa.String(length=255), nullable=True))
    op.add_column('payments', sa.Column('international', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('payments', sa.Column('captured', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('payments', sa.Column('amount_refunded', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.00'), nullable=False))
    op.add_column('payments', sa.Column('refund_status', sa.String(length=50), nullable=True))
    op.add_column('payments', sa.Column('description', sa.String(length=500), nullable=True))
    op.add_column('payments', sa.Column('error_source', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('error_step', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('error_reason', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('razorpay_created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payments', sa.Column('raw_payload', JSON_TYPE, nullable=True))

    op.create_index('ix_payments_razorpay_payment_id', 'payments', ['razorpay_payment_id'])
    op.create_index('ix_payments_razorpay_order_id', 'payments', ['razorpay_order_id'])


def downgrade() -> None:
    op.drop_index('ix_payments_razorpay_order_id', table_name='payments')
    op.drop_index('ix_payments_razorpay_payment_id', table_name='payments')
    op.drop_column('payments', 'raw_payload')
    op.drop_column('payments', 'razorpay_created_at')
    op.drop_column('payments', 'error_reason')
    op.drop_column('payments', 'error_step')
    op.drop_column('payments', 'error_source')
    op.drop_column('payments', 'description')
    op.drop_column('payments', 'refund_status')
    op.drop_column('payments', 'amount_refunded')
    op.drop_column('payments', 'captured')
    op.drop_column('payments', 'international')
    op.drop_column('payments', 'vpa')
    op.drop_column('payments', 'wallet')
    op.drop_column('payments', 'bank')
    op.drop_column('payments', 'razorpay_order_id')
    op.drop_column('payments', 'razorpay_payment_id')
