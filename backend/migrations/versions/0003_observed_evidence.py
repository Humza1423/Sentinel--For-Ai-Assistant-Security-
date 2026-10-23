"""Add observed evidence separately from legacy scripted campaign events."""

import sqlalchemy as sa
from alembic import op

revision = "0003_observed_evidence"
down_revision = "0002_synthetic_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observed_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("attempt_id", sa.String(36), nullable=True),
        sa.Column("origin", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "observed_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("observed_runs.run_id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "parent_event_id",
            sa.String(36),
            sa.ForeignKey("observed_events.event_id"),
            nullable=True,
        ),
        sa.Column("event_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("run_id", "sequence", name="uq_observed_run_sequence"),
    )
    # SQLite is the supported local store. These protect normal SQL/ORM writes;
    # an administrator can still replace the database or remove its triggers.
    for operation in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER observed_events_no_{operation.lower()} "
            f"BEFORE {operation} ON observed_events "
            "BEGIN SELECT RAISE(ABORT, 'Observed events are append-only'); END"
        )


def downgrade() -> None:
    op.drop_table("observed_events")
    op.drop_table("observed_runs")
