"""Add server-owned chat sessions and complete turns."""

import sqlalchemy as sa
from alembic import op

revision = "0005_chat_sessions"
down_revision = "0004_bank_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.String(36), primary_key=True),
        sa.Column("owner_digest", sa.String(64), nullable=False),
        sa.Column("customer_id", sa.String(32), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("target_digest", sa.String(64), nullable=False),
        sa.Column("active_request", sa.String(36)),
        sa.Column("worker_pid", sa.Integer()),
    )
    op.create_table(
        "chat_turns",
        sa.Column("turn_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id", sa.String(36), sa.ForeignKey("chat_sessions.session_id"), nullable=False
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("observed_runs.run_id"), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result_json", sa.Text()),
        sa.Column("messages_json", sa.Text()),
        sa.UniqueConstraint("session_id", "request_id"),
    )


def downgrade():
    op.drop_table("chat_turns")
    op.drop_table("chat_sessions")
