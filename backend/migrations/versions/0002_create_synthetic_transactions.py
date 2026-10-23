"""Persist the synthetic bank fixture as a versioned data table."""

import sqlalchemy as sa
from alembic import op

revision = "0002_synthetic_transactions"
down_revision = "0001_campaign_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(length=32), primary_key=True),
        sa.Column("customer_id", sa.String(length=32), nullable=False),
        sa.Column("merchant", sa.String(length=128), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("memo_provenance", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_transactions_customer_id", "transactions", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_customer_id", table_name="transactions")
    op.drop_table("transactions")
