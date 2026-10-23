"""Create campaign and run evidence tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_campaign_evidence"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("campaign_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "campaign_id",
            sa.String(length=36),
            sa.ForeignKey("campaigns.campaign_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_run_events_campaign_id", "run_events", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_run_events_campaign_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_table("campaigns")
