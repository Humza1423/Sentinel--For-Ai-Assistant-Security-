"""A provider-independent admission broker. All monetary amounts are USD micro-units."""

import argparse
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import case, func, select

from .store import BudgetAccountRow, Session, UsageChargeRow

PROJECT_LIMIT = 45_000_000
ASSESSMENT_LIMIT = 2_000_000
PRICE_VERSION = "openai-luna-standard-short-2026-10-24"
PRICE_SOURCE = "https://developers.openai.com/api/docs/models/gpt-6-luna"
VERIFIED_ON = date(2026, 10, 24)
# Micro-USD per million tokens: input, cached input, 30m/12h writes, output.
RATES = (100_000, 10_000, 125_000, 250_000, 500_000)


class BudgetError(RuntimeError):
    pass


class NotDispatched(RuntimeError):
    """Trusted adapter confirms no provider request was sent; safe to release."""


class Usage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    cache_write_30m_tokens: int = Field(default=0, ge=0)
    cache_write_12h_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_partitions(self):
        if (
            self.cached_input_tokens + self.cache_write_30m_tokens + self.cache_write_12h_tokens
            > self.input_tokens
        ):
            raise ValueError("Cache partitions exceed input tokens")
        if self.reasoning_tokens > self.output_tokens:
            raise ValueError("Reasoning is a subset of output, not an extra charge")
        return self


class CallPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    charge_id: UUID
    assessment_id: UUID | None = None
    run_id: UUID | None = None
    role: Literal["target", "attacker", "investigator", "defense", "coding", "formatter"]
    model: Literal["gpt-6-luna"] = "gpt-6-luna"
    price_version: Literal["openai-luna-standard-short-2026-10-24"] = PRICE_VERSION
    max_input_tokens: int = Field(default=12000, ge=1, le=12000, strict=True)
    max_output_tokens: int = Field(default=2000, ge=1, le=2000, strict=True)


def cost(usage: Usage) -> int:
    uncached = (
        usage.input_tokens
        - usage.cached_input_tokens
        - usage.cache_write_30m_tokens
        - usage.cache_write_12h_tokens
    )
    counts = (
        uncached,
        usage.cached_input_tokens,
        usage.cache_write_30m_tokens,
        usage.cache_write_12h_tokens,
        usage.output_tokens,
    )
    return (
        sum(count * rate for count, rate in zip(counts, RATES, strict=True)) + 999_999
    ) // 1_000_000


def maximum_cost(plan: CallPlan) -> int:
    # Assume all input could incur the highest supported cache-write rate.
    return (
        plan.max_input_tokens * max(RATES[:4]) + plan.max_output_tokens * RATES[4] + 999_999
    ) // 1_000_000


def liability(db, assessment_id=None):
    query = select(
        func.coalesce(
            func.sum(
                case(
                    (UsageChargeRow.status == "settled", UsageChargeRow.settled_micro_usd),
                    else_=UsageChargeRow.reserved_micro_usd,
                )
            ),
            0,
        )
    )
    if assessment_id is not None:
        query = query.where(UsageChargeRow.assessment_id == assessment_id)
    return db.scalar(query)


class UsageBroker:
    def __init__(self, session_factory=Session):
        self.sessions = session_factory

    def initialize(self, prior_micro_usd: int):
        if type(prior_micro_usd) is not int or not 0 <= prior_micro_usd <= PROJECT_LIMIT:
            raise ValueError("Prior spend must be an integer between zero and $45 in micro-USD")
        with self.sessions.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            account = db.get(BudgetAccountRow, "sentinel")
            if account.prior_micro_usd is not None:
                raise BudgetError("Budget already initialized; cannot reset prior spend")
            account.prior_micro_usd = prior_micro_usd
            account.started_at = datetime.now(UTC).isoformat()

    def summary(self):
        with self.sessions() as db:
            db.connection().exec_driver_sql("BEGIN")
            account = db.get(BudgetAccountRow, "sentinel")
            settled = db.scalar(
                select(func.coalesce(func.sum(UsageChargeRow.settled_micro_usd), 0)).where(
                    UsageChargeRow.status == "settled"
                )
            )
            reserved = db.scalar(
                select(func.coalesce(func.sum(UsageChargeRow.reserved_micro_usd), 0)).where(
                    UsageChargeRow.status != "settled"
                )
            )
            return {
                "currency": "USD",
                "unit": "micro_usd",
                "initialized": account.prior_micro_usd is not None,
                "accounting_started_at": account.started_at,
                "prior_micro_usd": account.prior_micro_usd,
                "recorded_micro_usd": settled,
                "reserved_micro_usd": reserved,
                "remaining_micro_usd": max(
                    0, PROJECT_LIMIT - account.prior_micro_usd - settled - reserved
                )
                if account.prior_micro_usd is not None
                else None,
                "project_limit_micro_usd": PROJECT_LIMIT,
                "assessment_limit_micro_usd": ASSESSMENT_LIMIT,
                "price_version": PRICE_VERSION,
                "price_verified_on": VERIFIED_ON.isoformat(),
                "price_source": PRICE_SOURCE,
                "live_adapter_available": False,
                "halted": bool(account.halted),
            }

    def _reserve(self, plan):
        if not 0 <= (datetime.now(UTC).date() - VERIFIED_ON).days <= 30:
            raise BudgetError("Price card must be reverified before dispatch")
        bound = maximum_cost(plan)
        with self.sessions.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            account = db.get(BudgetAccountRow, "sentinel")
            if account.halted:
                raise BudgetError("Accounting halted after adapter exceeded token bounds")
            if account.prior_micro_usd is None:
                raise BudgetError("Initialize prior spend before provider execution")
            if db.get(UsageChargeRow, str(plan.charge_id)):
                raise BudgetError("Attempt already recorded; never dispatch it twice")
            if account.prior_micro_usd + liability(db) + bound > PROJECT_LIMIT:
                raise BudgetError("Project budget exhausted")
            aid = str(plan.assessment_id) if plan.assessment_id else None
            if aid and liability(db, aid) + bound > ASSESSMENT_LIMIT:
                raise BudgetError("Assessment budget exhausted")
            db.add(
                UsageChargeRow(
                    charge_id=str(plan.charge_id),
                    assessment_id=aid,
                    role=plan.role,
                    status="uncertain",
                    reserved_micro_usd=bound,
                    plan_json=plan.model_dump_json(),
                )
            )

    def settle(self, charge_id, usage: Usage, provider_request_id: str | None = None):
        usage = Usage.model_validate_json(usage.model_dump_json())
        amount = cost(usage)
        with self.sessions.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = db.get(UsageChargeRow, str(charge_id))
            if row is None:
                raise BudgetError("Unknown attempt")
            if row.status == "settled":
                if row.usage_json != usage.model_dump_json():
                    raise BudgetError("Conflicting usage for settled attempt")
                return
            plan = CallPlan.model_validate_json(row.plan_json)
            row.status = "settled"
            row.settled_micro_usd = amount
            row.usage_json = usage.model_dump_json()
            row.provider_request_id = provider_request_id[:200] if provider_request_id else None
            exceeded = (
                usage.input_tokens > plan.max_input_tokens
                or usage.output_tokens > plan.max_output_tokens
            )
            if exceeded:
                db.get(BudgetAccountRow, "sentinel").halted = 1
        if exceeded:
            raise BudgetError("Adapter exceeded reserved token bounds; actual usage recorded")

    def execute(self, plan: CallPlan, operation):
        """Operation receives enforced limits and returns (result, Usage, request_id).

        T09's trusted adapter must apply these exact caps, standard processing,
        no regional uplift and no hidden retries. Every retry needs a fresh plan.
        """
        plan = CallPlan.model_validate_json(plan.model_dump_json())
        self._reserve(plan)
        try:
            result, usage, request_id = operation(plan)
            usage = Usage.model_validate(usage)
            self.settle(plan.charge_id, usage, request_id)
        except NotDispatched:
            self.settle(plan.charge_id, Usage(input_tokens=0, output_tokens=0))
            raise
        # Any other exception deliberately retains uncertain liability. A process
        # crash has the same durable outcome; elapsed time never releases money.
        return result


def estimate():
    from uuid import uuid4

    plan = CallPlan(charge_id=uuid4(), role="target")
    return {
        "scope": "one standard short-context call",
        "price_version": PRICE_VERSION,
        "assumed_input_tokens": 3000,
        "assumed_output_tokens": 500,
        "estimated_micro_usd": cost(Usage(input_tokens=3000, output_tokens=500)),
        "max_input_tokens": plan.max_input_tokens,
        "max_output_tokens": plan.max_output_tokens,
        "maximum_micro_usd": maximum_cost(plan),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Sentinel's USD accounting once")
    parser.add_argument("--prior-spend-usd", required=True, type=Decimal)
    args = parser.parse_args()
    micro = args.prior_spend_usd * 1_000_000
    if not micro.is_finite() or micro != micro.to_integral_value():
        parser.error("Use nonnegative USD with at most six decimal places")
    UsageBroker().initialize(int(micro))
    print(json.dumps(UsageBroker().summary(), indent=2))
