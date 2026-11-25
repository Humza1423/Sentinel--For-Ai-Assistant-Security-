from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from test_observed_scoring import context, trial
from test_runtime import ToolFake, call, final

from app.bank import BOB_ID
from app.evidence import read_events
from app.investigation import investigate_run
from app.remediation import propose_repair


@pytest.fixture
def investigation():
    run = trial(
        ToolFake(responses=[call("lookup_customer_transaction", {"customer_id": BOB_ID}), final()]),
        context(),
    )
    assert investigate_run(run.run_id).status == "explained"
    finding = read_events(run.run_id).events[-1]
    return run.run_id, finding.event_id


def test_proposal_links_original_investigation(investigation):
    report = propose_repair(*investigation)
    assert report.status == "proposed" and report.planner == "offline_fixture"
    saved = read_events(report.run_id).events[-1]
    assert saved.parent_event_id == investigation[1]
    assert saved.payload["revision"] == report.revision
    assert report.required_checks and report.target_digest
    assert propose_repair(report.run_id, uuid4()).status == "insufficient_evidence"


def test_model_proposal_is_scope_checked(investigation):
    plan = propose_repair(*investigation).plan

    class Analyst:
        def invoke_defense(self, messages):
            return AIMessage(content=plan.model_dump_json())

    assert propose_repair(*investigation, model=Analyst()).status == "proposed"
    plan.changes[0] = plan.changes[0].model_copy(
        update={"target": "backend/app/observed_scoring.py"}
    )
    report = propose_repair(*investigation, model=Analyst())
    assert report.status == "invalid_proposal" and report.event_id is None
    plan.changes[0] = plan.changes[0].model_copy(
        update={"kind": "reviewed_control", "target": "context_bound_customer_tools_v1"}
    )
    assert propose_repair(*investigation, model=Analyst()).status == "invalid_proposal"
