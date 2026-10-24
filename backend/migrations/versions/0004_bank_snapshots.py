"""Persist immutable bank snapshots and isolated memo overlays."""

import sqlalchemy as sa
from alembic import op

revision = "0004_bank_snapshots"
down_revision = "0003_observed_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bank_snapshots",
        sa.Column("snapshot_id", sa.String(64), primary_key=True),
        sa.Column("dataset_version", sa.String(32), nullable=False),
        sa.Column("reference_date", sa.String(10), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("contents_json", sa.Text(), nullable=False),
    )
    op.create_table(
        "bank_memo_overlays",
        sa.Column("overlay_id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column(
            "snapshot_id",
            sa.String(64),
            sa.ForeignKey("bank_snapshots.snapshot_id"),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.String(32), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("memo_provenance", sa.String(32), nullable=False),
        sa.UniqueConstraint("run_id", "transaction_id", name="uq_overlay_run_transaction"),
    )
    op.create_index("ix_bank_memo_overlays_run_id", "bank_memo_overlays", ["run_id"])
    for table in ("bank_snapshots", "bank_memo_overlays"):
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END"
            )


def downgrade() -> None:
    for table in ("bank_snapshots", "bank_memo_overlays"):
        for operation in ("update", "delete"):
            op.execute(f"DROP TRIGGER {table}_no_{operation}")
    op.drop_index("ix_bank_memo_overlays_run_id", table_name="bank_memo_overlays")
    op.drop_table("bank_memo_overlays")
    op.drop_table("bank_snapshots")
