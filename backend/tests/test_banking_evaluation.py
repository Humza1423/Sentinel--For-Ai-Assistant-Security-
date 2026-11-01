"""T13 checks real controls and assistant usefulness as separate evidence."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.bank import ALICE_ID, BOB_ID
from app.evaluation import (
    _customer_scope_valid,
    evaluate_banking_assistant,
    run_benign_suite,
    run_control_probes,
)
from app.evidence import read_events
from app.fixture_model import BankingFixtureModel
from app.target_contracts import RequestContext, TargetConfig
from app.targets import resolve_target


def context(customer_id=ALICE_ID):
    return RequestContext(
        session_id="t13-session",
        authenticated_customer_id=customer_id,
        request_id=str(uuid4()),
    )


def test_control_probes_exercise_reference_tools_and_link_verdicts_to_evidence():
    request_context = context()
    results = run_control_probes(TargetConfig(tool_profile="vulnerable_lookup_v1"), request_context)

    assert [result.probe_id for result in results] == [
        "protected_schema_rejects_customer_id",
        "gateway_denies_foreign_customer",
        "repository_denies_foreign_transaction_id",
        "repository_allows_owned_transaction",
    ]
    assert all(result.outcome == "passed" for result in results)
    for result in results:
        events = read_events(result.run_id).events
        event_ids = {event.event_id for event in events}
        assert set(result.event_ids) <= event_ids
        verdict = next(event for event in events if event.name == "scorer.verdict")
        assert verdict.event_id in result.event_ids
        assert verdict.payload["probe_id"] == result.probe_id
        assert set(verdict.payload["supporting_event_ids"]) <= {
            str(event_id) for event_id in event_ids
        }
        if result.probe_id == "protected_schema_rejects_customer_id":
            assert any(
                event.name == "tool.denied"
                and event.payload.get("reason_code") == "invalid_tool_arguments"
                for event in events
            )
            assert not any(event.name.startswith("repository.read_") for event in events)


def test_control_probes_select_a_foreign_identity_for_either_customer():
    results = run_control_probes(TargetConfig(), context(BOB_ID))

    assert all(result.outcome == "passed" for result in results)


def test_missing_or_inconsistent_ownership_evidence_cannot_pass():
    def read_event(record_ids, record_owners):
        return SimpleNamespace(
            name="repository.read_completed",
            payload={
                "outcome": "returned_data",
                "record_ids": record_ids,
                "record_owners": record_owners,
            },
        )

    assert not _customer_scope_valid((read_event(["T-1"], []),), ALICE_ID)
    assert not _customer_scope_valid((read_event(["T-1"], [BOB_ID]),), ALICE_ID)
    assert _customer_scope_valid((read_event(["T-1"], [ALICE_ID]),), ALICE_ID)


def test_live_benign_evaluation_requires_assessment_budget_before_model_creation():
    def model_factory(_recorder):
        pytest.fail("Must reject missing budget scope before model creation")

    with pytest.raises(ValueError, match="assessment budget scope"):
        run_benign_suite(
            config=TargetConfig(),
            context=context(),
            model_factory=model_factory,
            origin="live_execution",
        )


def test_evaluation_runs_five_benign_queries_through_selected_lab_assistant():
    request_context = context()
    config = TargetConfig(tool_profile="vulnerable_lookup_v1")
    created_models = []

    def model_factory(_recorder):
        model = BankingFixtureModel()
        created_models.append(model)
        return model

    report = evaluate_banking_assistant(
        config=config,
        context=request_context,
        model_factory=model_factory,
    )

    assert report.controls_passed
    assert report.usefulness_passed
    assert len(report.controls) == 4
    assert [case.case_id for case in report.benign_cases] == [
        "latest-transfer",
        "spending-summary",
        "grocery-spending",
        "latest-transaction",
        "out-of-scope-refusal",
    ]
    assert all(case.outcome == "passed" for case in report.benign_cases)
    assert all(case.origin == "fixture_execution" for case in report.benign_cases)
    assert len(created_models) == len(report.benign_cases)
    assert report.target_digest != report.reference_control_digest

    for case in report.benign_cases:
        events = read_events(case.run_id).events
        event_ids = {event.event_id for event in events}
        assert set(case.event_ids) <= event_ids
        assert any(event.name == "assistant.output" for event in events)
        assert any(event.name == "scorer.verdict" for event in events)
        request = next(event for event in events if event.name == "request.received")
        expected_digest = resolve_target(config, context=request_context).manifest().target_digest
        assert request.payload["target_digest"] == expected_digest
        assert request.payload["authenticated_customer_id"] == ALICE_ID


def test_evaluation_reports_failed_usefulness_separately_from_control_results():
    class RefusingModel(BankingFixtureModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            from langchain_core.messages import AIMessage
            from langchain_core.outputs import ChatGeneration, ChatResult

            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content='{"kind":"refusal","display_text":"I cannot help.","transaction_ids":[]}'
                        )
                    )
                ]
            )

    report = evaluate_banking_assistant(
        config=TargetConfig(),
        context=context(),
        model_factory=lambda _recorder: RefusingModel(),
    )

    assert all(probe.outcome == "passed" for probe in report.controls)
    assert report.controls_passed
    assert not report.usefulness_passed
    assert all(
        case.outcome == "failed"
        for case in report.benign_cases
        if case.case_id != "out-of-scope-refusal"
    )
    assert report.benign_cases[-1].outcome == "passed"
