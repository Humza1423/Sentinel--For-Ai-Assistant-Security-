"""Add durable local budget admission and per-attempt usage."""

import sqlalchemy as sa
from alembic import op

revision = "0006_usage_budget"
down_revision = "0005_chat_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "budget_account",
        sa.Column("account_id", sa.String(32), primary_key=True),
        sa.Column("started_at", sa.String(40)),
        sa.Column("prior_micro_usd", sa.Integer()),
        sa.Column("halted", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("INSERT INTO budget_account (account_id) VALUES ('sentinel')")
    op.create_table(
        "usage_charges",
        sa.Column("charge_id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("assessment_id", sa.String(36)),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("reserved_micro_usd", sa.Integer(), nullable=False),
        sa.Column("settled_micro_usd", sa.Integer()),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("usage_json", sa.Text()),
        sa.Column("provider_request_id", sa.String(200)),
    )
    op.create_index("ix_usage_charges_assessment_id", "usage_charges", ["assessment_id"])


def downgrade():
    op.drop_index("ix_usage_charges_assessment_id", "usage_charges")
    op.drop_table("usage_charges")
    op.drop_table("budget_account")
