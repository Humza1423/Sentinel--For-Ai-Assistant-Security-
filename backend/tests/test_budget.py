from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.budget import (
    ASSESSMENT_LIMIT,
    PROJECT_LIMIT,
    BudgetError,
    CallPlan,
    NotDispatched,
    Usage,
    UsageBroker,
    cost,
    maximum_cost,
)
from app.store import Base, BudgetAccountRow, UsageChargeRow


@pytest.fixture
def broker(tmp_path, monkeypatch):
    monkeypatch.setattr("app.budget.VERIFIED_ON", datetime.now(UTC).date())
    engine = create_engine(
        f"sqlite:///{tmp_path / 'budget.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions.begin() as db:
        db.add(BudgetAccountRow(account_id="sentinel", halted=0))
    yield UsageBroker(sessions)
    engine.dispose()


def plan(**kwargs):
    return CallPlan(charge_id=uuid4(), role="target", **kwargs)


def test_exact_prices_cache_partitions_reasoning_and_rounding():
    assert cost(Usage(input_tokens=1000, output_tokens=100)) == 150
    assert (
        cost(
            Usage(
                input_tokens=1000,
                output_tokens=100,
                cached_input_tokens=200,
                cache_write_30m_tokens=300,
                reasoning_tokens=40,
            )
        )
        == 140
    )
    assert cost(Usage(input_tokens=1, output_tokens=0)) == 1
    assert maximum_cost(plan()) == 4000
    with pytest.raises(ValidationError):
        Usage(input_tokens=10, output_tokens=0, cached_input_tokens=11)
    with pytest.raises(ValidationError):
        Usage(input_tokens=True, output_tokens=0)


def test_initialization_dispatch_usage_and_idempotent_settlement(broker):
    called = []
    p = plan()

    def operation(limits):
        called.append(limits)
        return "answer", Usage(input_tokens=1000, output_tokens=100), "req_example"

    with pytest.raises(BudgetError, match="Initialize"):
        broker.execute(p, operation)
    assert called == []
    broker.initialize(100)
    assert broker.execute(p, operation) == "answer"
    broker.settle(p.charge_id, Usage(input_tokens=1000, output_tokens=100))
    with pytest.raises(BudgetError, match="already recorded"):
        broker.execute(p, operation)
    assert len(called) == 1
    assert broker.summary()["remaining_micro_usd"] == PROJECT_LIMIT - 250
    with pytest.raises(BudgetError, match="Conflicting"):
        broker.settle(p.charge_id, Usage(input_tokens=1, output_tokens=1))
    with pytest.raises(BudgetError, match="already initialized"):
        broker.initialize(0)


def test_uncertain_calls_survive_restart_and_retries_reserve_again(broker):
    broker.initialize(0)

    def timeout(_):
        raise TimeoutError("unknown billing")

    for _ in range(2):
        with pytest.raises(TimeoutError):
            broker.execute(plan(), timeout)
    restarted = UsageBroker(broker.sessions)
    assert restarted.summary()["reserved_micro_usd"] == 8000

    def not_sent(_):
        raise NotDispatched

    with pytest.raises(NotDispatched):
        restarted.execute(plan(), not_sent)
    assert restarted.summary()["reserved_micro_usd"] == 8000


def test_concurrent_project_reservations_cannot_overspend(broker):
    broker.initialize(PROJECT_LIMIT - 4000)

    def attempt(_):
        def timeout(_):
            raise TimeoutError

        try:
            broker.execute(plan(), timeout)
        except (TimeoutError, BudgetError) as exc:
            return type(exc).__name__

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sorted(outcomes) == ["BudgetError", "TimeoutError"]
    assert broker.summary()["remaining_micro_usd"] == 0


def test_assessment_ceiling_and_overrun_freeze(broker):
    broker.initialize(0)
    assessment = uuid4()
    seed = plan(assessment_id=assessment)
    with broker.sessions.begin() as db:
        db.add(
            UsageChargeRow(
                charge_id=str(seed.charge_id),
                assessment_id=str(assessment),
                role="target",
                status="uncertain",
                reserved_micro_usd=ASSESSMENT_LIMIT - 3999,
                plan_json=seed.model_dump_json(),
            )
        )
    with pytest.raises(BudgetError, match="Assessment"):
        broker.execute(plan(assessment_id=assessment), lambda _: pytest.fail("must not dispatch"))
    with pytest.raises(BudgetError, match="exceeded"):
        broker.execute(
            plan(), lambda _: ("answer", Usage(input_tokens=12001, output_tokens=2000), None)
        )
    with pytest.raises(BudgetError, match="halted"):
        broker.execute(plan(), lambda _: pytest.fail("must not dispatch"))
    assert broker.summary()["recorded_micro_usd"] > 0


def test_expired_prices_and_missing_usage_fail_closed(broker, monkeypatch):
    broker.initialize(0)
    with pytest.raises(ValidationError):
        broker.execute(plan(), lambda _: ("answer", {}, None))
    assert broker.summary()["reserved_micro_usd"] == 4000
    monkeypatch.setattr("app.budget.VERIFIED_ON", datetime.now(UTC).date() - timedelta(days=31))
    with pytest.raises(BudgetError, match="reverified"):
        broker.execute(plan(), lambda _: pytest.fail("must not dispatch"))
