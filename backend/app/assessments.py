"""Persistent, owner-scoped local usefulness assessments."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from .chat import require_session
from .evaluation import run_benign_suite, run_control_probes, run_session_bound_probes
from .execution_control import ExecutionCancelled, check_execution, on_run_started
from .fixture_model import BankingFixtureModel
from .registered_verification import (
    compare_banking_cases,
    copy_with_session_binding,
    inspect_customer_scope,
    recommend_session_binding,
    verification_outcome,
)
from .store import AssessmentEventRow, AssessmentRow, Session
from .target_contracts import RequestContext, TargetConfig

ACTIVE = ("queued", "running")


def _event(db, row, kind, **data):
    sequence = (
        db.scalar(
            select(AssessmentEventRow.sequence)
            .where(AssessmentEventRow.assessment_id == row.assessment_id)
            .order_by(AssessmentEventRow.sequence.desc())
            .limit(1)
        )
        or 0
    )
    db.add(
        AssessmentEventRow(
            assessment_id=row.assessment_id,
            sequence=sequence + 1,
            payload_json=json.dumps(
                {
                    "type": kind,
                    "status": row.status,
                    "timestamp": datetime.now(UTC).isoformat(),
                    **data,
                }
            ),
        )
    )


def create_assessment(session_id, owner, request_id):
    with Session.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        session = require_session(db, session_id, owner)
        old = db.scalar(
            select(AssessmentRow).where(
                AssessmentRow.session_id == session_id, AssessmentRow.request_id == request_id
            )
        )
        if old:
            return old.assessment_id, False
        if db.scalar(select(AssessmentRow).where(AssessmentRow.status.in_(ACTIVE))):
            raise ValueError("Another assessment is already running")
        row = AssessmentRow(
            assessment_id=str(uuid4()),
            session_id=session_id,
            request_id=request_id,
            status="queued",
            cancel_requested=0,
            config_json=session.config_json,
        )
        db.add(row)
        db.flush()
        _event(
            db, row, "queued", mode="fixture_execution", scope="usefulness_and_reference_controls"
        )
        return row.assessment_id, True


def read_assessment(assessment_id, owner, after=0):
    with Session() as db:
        row = db.get(AssessmentRow, assessment_id)
        if row is None:
            raise LookupError("Assessment unavailable")
        require_session(db, row.session_id, owner)
        events = db.scalars(
            select(AssessmentEventRow)
            .where(
                AssessmentEventRow.assessment_id == assessment_id,
                AssessmentEventRow.sequence > after,
            )
            .order_by(AssessmentEventRow.sequence)
        ).all()
        return {
            "assessment_id": assessment_id,
            "status": row.status,
            "mode": "fixture_execution",
            "scope": "usefulness_and_reference_controls",
            "report": json.loads(row.report_json) if row.report_json else None,
            "events": [
                {"sequence": event.sequence, **json.loads(event.payload_json)} for event in events
            ],
        }


def cancel_assessment(assessment_id, owner):
    read_assessment(assessment_id, owner)
    with Session.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        row = db.get(AssessmentRow, assessment_id)
        if row.status in ACTIVE and not row.cancel_requested:
            row.cancel_requested = 1
            if row.status == "queued":
                row.status = "cancelled"
            _event(db, row, "cancellation_requested")


def execute_assessment(assessment_id):
    with Session.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        row = db.get(AssessmentRow, assessment_id)
        if row is None or row.status != "queued":
            return
        row.status = "running"
        _event(db, row, "started")
        config_json = row.config_json
        from .store import ChatSessionRow

        session = db.get(ChatSessionRow, row.session_id)
        customer_id = session.customer_id
        session_id = row.session_id

    def check():
        with Session() as db:
            row = db.get(AssessmentRow, assessment_id)
            if row.cancel_requested or row.status != "running":
                raise ExecutionCancelled("Assessment cancelled")

    def progress(kind, result):
        check()
        with Session.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = db.get(AssessmentRow, assessment_id)
            _event(
                db,
                row,
                kind,
                result=result if isinstance(result, dict) else result.model_dump(mode="json"),
            )

    def record_run(run_id):
        # Link ownership before any tool/model content is recorded, including runs
        # that are cancelled before a complete case result can be saved.
        with Session.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            row = db.get(AssessmentRow, assessment_id)
            _event(db, row, "run_started", result={"run_id": str(run_id)})

    token = check_execution.set(check)
    observer_token = on_run_started.set(record_run)
    try:
        check()
        config = TargetConfig.model_validate_json(config_json)
        context = RequestContext(
            session_id=session_id,
            authenticated_customer_id=customer_id,
            request_id=str(uuid4()),
        )
        inspection = inspect_customer_scope(config, context)
        progress("baseline_scope_checked", inspection)
        recommendation = recommend_session_binding(inspection)
        if recommendation:
            progress("defense_recommended", recommendation)
            candidate_config = copy_with_session_binding(config)
            candidate_scope = inspect_customer_scope(candidate_config, context)
            progress("candidate_scope_checked", candidate_scope)
            controls = run_session_bound_probes(
                candidate_config, context, on_result=lambda r: progress("reference_control", r)
            )
        else:
            controls = run_control_probes(
                config, context, on_result=lambda r: progress("reference_control", r)
            )

        def factory(recorder):
            check()
            return BankingFixtureModel()

        benign = run_benign_suite(
            config=config,
            context=context,
            model_factory=factory,
            on_result=lambda r: progress("benign_case", r),
        )
        report = {
            "mode": "fixture_execution",
            "scope": "usefulness_and_reference_controls",
            "target_config": config.model_dump(mode="json"),
            "controls": [r.model_dump(mode="json") for r in controls],
            "benign": [r.model_dump(mode="json") for r in benign],
        }
        report["baseline_scope"] = inspection
        report["recommendation"] = recommendation
        if recommendation:
            candidate = run_benign_suite(
                config=candidate_config,
                context=context,
                model_factory=factory,
                on_result=lambda r: progress("candidate_benign_case", r),
            )
            comparisons = compare_banking_cases(benign, candidate)
            report["verification"] = {
                "status": verification_outcome(
                    candidate_scope, controls, benign, candidate, comparisons
                ),
                "candidate_scope": candidate_scope,
                "configuration_change": {
                    "defense_presets": {
                        "before": list(config.defense_presets),
                        "after": list(candidate_config.defense_presets),
                    }
                },
                "candidate_benign": [r.model_dump(mode="json") for r in candidate],
                "comparisons": comparisons,
            }
            progress("verification_completed", {"outcome": report["verification"]["status"]})
        finish(assessment_id, "complete", report)
    except ExecutionCancelled:
        finish(assessment_id, "cancelled")
    except Exception:  # noqa: BLE001 - retain progress without exposing provider or database details
        finish(assessment_id, "failed")
    finally:
        on_run_started.reset(observer_token)
        check_execution.reset(token)


def finish(assessment_id, status, report=None):
    with Session.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        row = db.get(AssessmentRow, assessment_id)
        if row is None or row.status not in ACTIVE:
            return
        row.status = "cancelled" if row.cancel_requested else status
        row.report_json = json.dumps(report) if report and row.status == "complete" else None
        _event(db, row, row.status)


def recover_assessments():
    with Session.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        for row in db.scalars(select(AssessmentRow).where(AssessmentRow.status.in_(ACTIVE))):
            row.status = "interrupted"
            _event(db, row, "interrupted")
