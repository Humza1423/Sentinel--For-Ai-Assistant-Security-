"""Persist local assessment progress and completed reports."""

import sqlalchemy as sa
from alembic import op

revision = "0008_assessments"
down_revision = "0007_live_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessments",
        sa.Column("assessment_id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id", sa.String(36), sa.ForeignKey("chat_sessions.session_id"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("cancel_requested", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("report_json", sa.Text()),
        sa.UniqueConstraint("session_id", "request_id"),
    )
    op.create_table(
        "assessment_events",
        sa.Column(
            "assessment_id",
            sa.String(36),
            sa.ForeignKey("assessments.assessment_id"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )


def downgrade():
    op.drop_table("assessment_events")
    op.drop_table("assessments")
