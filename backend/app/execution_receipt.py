"""Fingerprints computed where the built-in assistant consumes its inputs."""

import hashlib

from sqlalchemy import select

from .bank import SnapshotBankRepository
from .evidence import canonical_json
from .store import BankMemoOverlayRow, Session


def fingerprint(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def execution_receipt(config, context, user_message, history, schemas, overlay_run_id):
    snapshot = SnapshotBankRepository().snapshot
    with Session() as db:
        overlays = (
            db.scalars(
                select(BankMemoOverlayRow).where(BankMemoOverlayRow.run_id == overlay_run_id)
            ).all()
            if overlay_run_id
            else []
        )
        memo = sorted(
            [
                {
                    "transaction_id": row.transaction_id,
                    "snapshot_id": row.snapshot_id,
                    "memo": row.memo,
                    "provenance": row.memo_provenance,
                }
                for row in overlays
            ],
            key=lambda item: item["transaction_id"],
        )
    return {
        "schema_version": "1.0",
        "user_digest": fingerprint(user_message),
        "history_digest": fingerprint([message.model_dump(mode="json") for message in history]),
        "session_id": context.session_id,
        "customer_id": context.authenticated_customer_id,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_digest": snapshot.digest,
        "memo_digest": fingerprint(memo),
        "config": config.model_dump(mode="json"),
        "tool_schema_digest": fingerprint(schemas),
    }
