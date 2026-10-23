import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.assistant import make_bank_tools
from app.bank import ALICE_ID, BOB_ID, BOB_MARKER, BankRepository
from app.evidence import EvidenceError, EvidenceRecorder, read_events
from app.target_contracts import RequestContext, TargetConfig
from app.targets import resolve_target


def context():
    return RequestContext(
        session_id="observed-test", authenticated_customer_id=ALICE_ID, request_id=str(uuid4())
    )


def test_real_tool_to_repository_trace_and_causality():
    recorder = EvidenceRecorder.start()
    target = resolve_target(TargetConfig(), context=context(), evidence=recorder)
    output = target.bank_profile.tools[0].invoke({})
    assert "T-102" in output
    events = read_events(recorder.run_id).events
    assert [e.name for e in events] == [
        "target.resolved",
        "tool.requested",
        "arguments.validated",
        "authorization.decided",
        "tool.effective_arguments",
        "authorization.decided",
        "repository.read_started",
        "repository.read_completed",
        "tool.completed",
    ]
    requested = events[1]
    tool_decision, effective, repo_decision, started, completed = events[3:8]
    assert tool_decision.parent_event_id == requested.event_id
    assert effective.parent_event_id == tool_decision.event_id
    assert repo_decision.parent_event_id == effective.event_id
    assert started.parent_event_id == repo_decision.event_id
    assert completed.parent_event_id == started.event_id
    assert effective.payload["effective_customer_id"] == ALICE_ID
    assert completed.payload["record"]["customer_id"] == ALICE_ID
    assert completed.provenance["record.memo"] == "external_untrusted"
    assert not any(
        e.name.startswith(("model.", "context.", "defense.", "investigation.")) for e in events
    )


@pytest.mark.parametrize("invocation", ["invoke", "run", "ainvoke", "tool_call"])
def test_malformed_requests_are_recorded_without_a_read(invocation, monkeypatch):
    recorder = EvidenceRecorder.start()
    repository = BankRepository()

    def forbidden_read(*args, **kwargs):
        pytest.fail("Rejected tool arguments must not invoke the repository")

    monkeypatch.setattr(repository, "latest_for", forbidden_read)
    tool = make_bank_tools(defended=True, repository=repository, evidence=recorder)[0]
    arguments = {"customer_id": BOB_ID}
    with pytest.raises(ValidationError):
        if invocation == "ainvoke":
            asyncio.run(tool.ainvoke(arguments))
        elif invocation == "tool_call":
            tool.invoke({"name": tool.name, "type": "tool_call", "id": "call-1", "args": arguments})
        else:
            getattr(tool, invocation)(arguments)
    events = read_events(recorder.run_id).events
    assert [e.name for e in events] == ["tool.requested", "tool.denied"]
    assert events[-1].payload["reason_code"] == "invalid_tool_arguments"


def test_repository_denial_records_actual_decision_without_read(monkeypatch):
    repository = BankRepository()
    recorder = EvidenceRecorder.start()

    def forbidden_query(*args, **kwargs):
        pytest.fail("Denied ownership check must not open a banking query session")

    monkeypatch.setattr("app.bank.Session", forbidden_query)
    with recorder.bind(), pytest.raises(PermissionError):
        repository.get_for(BOB_ID, ALICE_ID, vulnerable=False)
    events = read_events(recorder.run_id).events
    assert len(events) == 1
    assert events[0].actor == "repository"
    assert events[0].payload["decision"] == "denied"
    assert events[0].payload["requested_customer_id"] == BOB_ID
    assert events[0].payload["authenticated_customer_id"] == ALICE_ID


def test_lab_read_is_real_but_not_mislabeled_as_model_context_delivery():
    recorder = EvidenceRecorder.start()
    tool = make_bank_tools(defended=False, evidence=recorder)[0]
    assert BOB_MARKER in tool.invoke({"customer_id": BOB_ID})
    events = read_events(recorder.run_id).events
    read = next(e for e in events if e.name == "repository.read_completed")
    assert read.payload["record"]["customer_id"] == BOB_ID
    assert not any(e.name.startswith("context.") for e in events)
    assert BOB_MARKER not in " ".join(e.model_dump_json() for e in events)


def test_missing_record_is_not_a_successful_data_read():
    recorder = EvidenceRecorder.start()
    tool = make_bank_tools(defended=False, evidence=recorder)[0]
    assert tool.invoke({"customer_id": "C-nonexistent"}) == "No matching transaction."
    events = read_events(recorder.run_id).events
    completed = next(e for e in events if e.name == "repository.read_completed")
    assert completed.payload == {"outcome": "no_data", "record": None}


def test_repository_failure_keeps_partial_evidence_without_sensitive_error_text(monkeypatch):
    repository = BankRepository()
    recorder = EvidenceRecorder.start()
    tool = make_bank_tools(defended=True, repository=repository, evidence=recorder)[0]

    def failed():
        raise OperationalError("synthetic-sensitive-error", None, None)

    monkeypatch.setattr("app.bank.Session", failed)
    with pytest.raises(OperationalError):
        tool.invoke({})
    events = read_events(recorder.run_id).events
    assert events[-2].name == "repository.read_failed"
    assert events[-1].name == "tool.failed"
    assert not any(e.name in ("repository.read_completed", "tool.completed") for e in events)
    assert "synthetic-sensitive-error" not in " ".join(e.model_dump_json() for e in events)


def test_failed_recorder_prevents_tool_execution():
    recorder = EvidenceRecorder.start()

    class BrokenStore:
        @staticmethod
        def begin():
            raise OperationalError("do not expose details", None, None)

    tool = make_bank_tools(defended=True, evidence=replace(recorder, session_factory=BrokenStore))[
        0
    ]
    with pytest.raises(EvidenceError, match="persist evidence"):
        tool.invoke({})
    assert read_events(recorder.run_id).events == ()


def test_recording_failure_after_read_never_emits_tool_success(monkeypatch):
    recorder = EvidenceRecorder.start()
    tool = make_bank_tools(defended=True, evidence=recorder)[0]
    original_append = EvidenceRecorder.append

    def append(self, name, *args, **kwargs):
        if name == "repository.read_completed":
            raise EvidenceError("recording unavailable")
        return original_append(self, name, *args, **kwargs)

    monkeypatch.setattr(EvidenceRecorder, "append", append)
    with pytest.raises(EvidenceError):
        tool.invoke({})
    names = [e.name for e in read_events(recorder.run_id).events]
    assert "repository.read_started" in names
    assert "repository.read_completed" not in names
    assert "tool.completed" not in names


def test_validation_error_inside_repository_is_a_failure_not_an_argument_denial(monkeypatch):
    repository = BankRepository()
    recorder = EvidenceRecorder.start()
    tool = make_bank_tools(defended=True, repository=repository, evidence=recorder)[0]

    def bad_record(*args):
        TargetConfig.model_validate({"unknown": True})

    monkeypatch.setattr(repository, "_record", bad_record)
    with pytest.raises(ValidationError):
        tool.invoke({})
    events = read_events(recorder.run_id).events
    assert "arguments.validated" in [e.name for e in events]
    assert events[-2].name == "repository.read_failed"
    assert events[-1].name == "tool.failed"
    assert "tool.denied" not in [e.name for e in events]


def test_async_tool_execution_preserves_run_context_and_resets_afterward():
    first, second = EvidenceRecorder.start(), EvidenceRecorder.start()
    first_tool = make_bank_tools(defended=True, evidence=first)[0]
    second_tool = make_bank_tools(defended=False, evidence=second)[0]

    async def both():
        return await asyncio.gather(
            first_tool.ainvoke({}), second_tool.ainvoke({"customer_id": BOB_ID})
        )

    outputs = asyncio.run(both())
    assert BOB_MARKER not in outputs[0] and BOB_MARKER in outputs[1]
    for recorder, customer in ((first, ALICE_ID), (second, BOB_ID)):
        events = read_events(recorder.run_id).events
        assert (
            next(e for e in events if e.name == "repository.read_completed").payload["record"][
                "customer_id"
            ]
            == customer
        )
        ids = {e.event_id for e in events}
        assert all(e.parent_event_id is None or e.parent_event_id in ids for e in events)
        assert events[-1].name == "tool.completed"
