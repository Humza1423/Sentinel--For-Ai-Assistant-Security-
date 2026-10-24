from datetime import date

import pytest
from sqlalchemy import text

from app.bank import ALICE_ID, BOB_ID, SnapshotBankRepository
from app.store import Session
from app.target_contracts import RequestContext


def context(customer=ALICE_ID):
    return RequestContext(
        session_id="test-session", authenticated_customer_id=customer, request_id="test-request"
    )


def test_snapshot_is_repeatable_and_persisted():
    first = SnapshotBankRepository().snapshot
    second = SnapshotBankRepository().snapshot
    assert first.snapshot_id == second.snapshot_id
    assert first.digest == second.digest
    assert first.dataset_version == "sentinel-bank-v2"
    assert first.reference_date == date(2026, 10, 23)
    assert len(first.transactions) == 120
    assert all(
        item.currency == "CAD" and isinstance(item.amount_cents, int) for item in first.transactions
    )


def test_scoped_queries_use_integer_cents_and_inclusive_dates():
    repository = SnapshotBankRepository()
    boundary = date(2026, 10, 23)
    rows = repository.transactions(context(), start=boundary, end=boundary)
    assert rows
    assert all(item.customer_id == ALICE_ID and item.date == boundary for item in rows)
    assert repository.spending_total(context(), start=boundary, end=boundary) == sum(
        abs(item.amount_cents) for item in rows if item.category not in {"income", "transfer"}
    )
    with pytest.raises(ValueError):
        repository.transactions(context(), start=boundary, end=date(2026, 10, 22))


def test_fixture_total_matches_independent_cents_oracle_and_date_edges():
    repository = SnapshotBankRepository()
    # Independently derive the expected result from the documented 8-row fixture cycle.
    expected = sum(
        (4250, 1895, 330, 1425, 2840, 0, 0, 1275)[index % 8]
        for index in range(30)
        if index % 3 != 2
    )
    start, end = date(2026, 9, 24), date(2026, 10, 23)
    assert repository.spending_total(context(), start=start, end=end) == expected
    comparison = repository.compare_spending(
        context(),
        first_start=date(2026, 10, 22),
        first_end=date(2026, 10, 23),
        second_start=date(2026, 10, 20),
        second_end=date(2026, 10, 21),
    )
    assert (
        comparison["change_cents"]
        == comparison["second_period_cents"] - comparison["first_period_cents"]
    )
    assert all(item.date <= end for item in repository.transactions(context(), end=end))
    assert all(item.date >= start for item in repository.transactions(context(), start=start))
    assert all(
        item.category == "groceries"
        for item in repository.transactions(context(), category="groceries")
    )
    payroll = next(item for item in repository.snapshot.transactions if item.category == "income")
    assert payroll.amount_cents > 0
    assert (
        repository.spending_total(
            context(), start=payroll.date, end=payroll.date, category="income"
        )
        == 0
    )


def test_foreign_records_are_not_returned_or_overlaid():
    repository = SnapshotBankRepository()
    bob = next(item for item in repository.snapshot.transactions if item.customer_id == BOB_ID)
    assert all(item.customer_id == ALICE_ID for item in repository.transactions(context()))
    with pytest.raises(LookupError):
        repository.apply_memo_overlay(context(), "run-a", bob.transaction_id, "attack")


def test_memo_overlay_is_run_specific_and_does_not_change_snapshot():
    repository = SnapshotBankRepository()
    row = repository.transactions(context(), limit=1)[0]
    original_digest = repository.snapshot.digest
    repository.apply_memo_overlay(context(), "run-a", row.transaction_id, "untrusted text")
    assert repository.apply_overlay_to(context(), "run-a", row).memo == "untrusted text"
    assert (
        repository.apply_overlay_to(context(), "run-a", row).memo_provenance == "external_untrusted"
    )
    assert repository.apply_overlay_to(context(), "run-b", row) == row
    assert repository.snapshot.digest == original_digest


def test_snapshot_and_overlay_rows_reject_normal_database_mutation():
    repository = SnapshotBankRepository()
    row = repository.transactions(context(), limit=1)[0]
    repository.apply_memo_overlay(context(), "run-immutable", row.transaction_id, "isolated")
    with Session.begin() as session, pytest.raises(Exception, match="immutable"):
        session.execute(
            text("UPDATE bank_snapshots SET contents_json='{}' WHERE snapshot_id=:id"),
            {"id": repository.snapshot.snapshot_id},
        )


def test_repository_snapshot_cannot_be_replaced_after_integrity_validation():
    repository = SnapshotBankRepository()
    forged = repository.snapshot.model_copy(update={"digest": "forged"})
    with pytest.raises((AttributeError, TypeError)):
        repository.snapshot = forged
    with pytest.raises((AttributeError, TypeError)):
        repository._snapshot = forged
    assert not hasattr(repository, "__dict__")
