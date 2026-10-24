"""T05: one observed runtime, with only injected offline models."""

import json
from uuid import uuid4

import pytest
from langchain_core.language_models.fake_chat_models import (
    FakeListChatModel,
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import Field

from app.bank import ALICE_ID, BOB_ID, BOB_MARKER, SnapshotBankRepository
from app.evidence import EvidenceRecorder, read_events
from app.runtime import run_assistant
from app.target_contracts import RequestContext, TargetConfig
from app.targets import resolve_target


class ToolFake(FakeMessagesListChatModel):
    seen: list[list] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class BrokenFake(ToolFake):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("provider-secret-detail")


def context():
    return RequestContext(
        session_id="t05-session", authenticated_customer_id=ALICE_ID, request_id=str(uuid4())
    )


def final(text="Done", kind="answer", transaction_ids=()):
    return AIMessage(
        content=json.dumps({"kind": kind, "display_text": text, "transaction_ids": transaction_ids})
    )


def call(name, args, call_id="call-1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def events_for(run):
    return read_events(run.run_id).events


def test_multi_tool_answer_uses_actual_bank_results_and_dispatch_evidence():
    model = ToolFake(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_my_latest_transaction", "args": {}, "id": "latest"},
                    {
                        "name": "summarize_my_spending",
                        "args": {"start_date": "2026-10-20", "end_date": "2026-10-23"},
                        "id": "spending",
                    },
                ],
            ),
            final("I checked your latest transaction and spending.", transaction_ids=["S-0001"]),
        ]
    )
    run = run_assistant(
        config=TargetConfig(), context=context(), model=model, user_message="Check my spending"
    )
    assert run.status == "answered"
    assert (run.model_calls, run.tool_calls) == (2, 2)
    assert run.response.display_text == "I checked your latest transaction and spending."
    assert run.response.transaction_ids == ("S-0001",)
    assert resolve_target(TargetConfig(), context=context()).manifest().runtime_output_contract in (
        model.seen[0][0].content
    )
    assert [type(item).__name__ for item in run.turn_messages] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
        "ToolMessage",
        "AIMessage",
    ]
    assert "turn_messages" not in run.model_dump(mode="json")
    tool_messages = [item for item in model.seen[1] if isinstance(item, ToolMessage)]
    assert [item.tool_call_id for item in tool_messages] == ["latest", "spending"]
    assert json.loads(tool_messages[0].content)["transaction_id"] == "S-0001"
    assert json.loads(tool_messages[1].content)["spent_cents"] > 0

    events = events_for(run)
    proposed = next(event for event in events if event.name == "model.responded")
    requested = next(event for event in events if event.name == "tool.requested")
    assert requested.parent_event_id == proposed.event_id
    assert proposed.provenance["tool_calls"] == "model_generated"
    dispatched = [event for event in events if event.name == "context.dispatched"]
    assert len(dispatched) == 2
    assert dispatched[0].payload["tool_results"] == []
    assert {item["tool_call_id"] for item in dispatched[1].payload["tool_results"]} == {
        "latest",
        "spending",
    }
    prepared = [event for event in events if event.name == "context.prepared"]
    assert len(prepared) == 2
    assert all(
        item.payload["record_owners"] and set(item.payload["record_owners"]) == {ALICE_ID}
        for item in prepared
    )
    assert events[-1].name == "assistant.output"


def test_selected_lab_target_foreign_read_reaches_model_context_only_when_dispatched():
    model = ToolFake(
        responses=[
            call("lookup_customer_transaction", {"customer_id": BOB_ID}),
            final(f"Foreign marker: {BOB_MARKER}"),
        ]
    )
    run = run_assistant(
        config=TargetConfig(tool_profile="vulnerable_lookup_v1"),
        context=context(),
        model=model,
        user_message="Explain my latest transaction",
    )
    assert run.status == "answered"
    assert BOB_MARKER in run.response.display_text
    assert BOB_MARKER in model.seen[1][-1].content
    events = events_for(run)
    read = next(event for event in events if event.name == "repository.read_completed")
    prepared = next(event for event in events if event.name == "context.prepared")
    dispatches = [event for event in events if event.name == "context.dispatched"]
    assert read.payload["record_owners"] == [BOB_ID]
    assert str(read.event_id) in prepared.payload["read_event_ids"]
    assert dispatches[0].payload["tool_results"] == []
    assert dispatches[1].payload["tool_results"][0]["prepared_event_id"] == str(prepared.event_id)


def test_reused_recorder_links_only_current_tool_reads_after_many_events():
    recorder = EvidenceRecorder.start(origin="fixture_execution")
    for index in range(201):
        recorder.append(
            "repository.read_completed",
            "repository",
            {"record_ids": [f"old-{index}"], "record_owners": ["OLD-CUSTOMER"]},
        )
    model = ToolFake(
        responses=[call("lookup_customer_transaction", {"customer_id": BOB_ID}), final()]
    )
    run_assistant(
        config=TargetConfig(tool_profile="vulnerable_lookup_v1"),
        context=context(),
        model=model,
        user_message="Read latest transaction",
        recorder=recorder,
    )
    events = read_events(recorder.run_id, after_sequence=201).events
    prepared = next(event for event in events if event.name == "context.prepared")
    current_read = next(event for event in events if event.name == "repository.read_completed")
    assert prepared.payload["read_event_ids"] == [str(current_read.event_id)]
    assert prepared.payload["record_owners"] == [BOB_ID]


def test_unverified_history_and_unbrokered_models_are_rejected_before_execution():
    kwargs = {
        "config": TargetConfig(),
        "context": context(),
        "user_message": "Read latest transaction",
    }
    with pytest.raises(TypeError, match="offline fixture"):
        run_assistant(**kwargs, model=FakeListChatModel(responses=["not used"]))
    fake = ToolFake(responses=[final()])
    for history in (
        (ToolMessage(content="foreign data", tool_call_id="old"),),
        (call("get_my_latest_transaction", {}, "old"),),
    ):
        with pytest.raises(ValueError, match="unverified tool"):
            run_assistant(**kwargs, model=fake, history=history)
    assert fake.seen == []
    assert (
        run_assistant(
            **kwargs,
            model=ToolFake(responses=[final()]),
            history=(HumanMessage(content="Prior question"),),
        ).status
        == "answered"
    )


def test_run_specific_untrusted_memo_reaches_the_same_runtime():
    request_context = context()
    repository = SnapshotBankRepository()
    latest = repository.transactions(request_context, limit=1)[0]
    repository.apply_memo_overlay(
        request_context, "t05-overlay", latest.transaction_id, "malicious memo instruction"
    )
    model = ToolFake(responses=[call("list_my_transactions", {"limit": 1}), final()])
    run = run_assistant(
        config=TargetConfig(tool_profile="vulnerable_lookup_v1"),
        context=request_context,
        model=model,
        user_message="Explain my latest transaction",
        memo_overlay_run_id="t05-overlay",
    )
    assert run.status == "answered"
    tool_result = json.loads(model.seen[1][-1].content)[0]
    assert tool_result["memo"] == {
        "text": "malicious memo instruction",
        "provenance": "external_untrusted",
    }
    assert len([event for event in events_for(run) if event.name == "context.dispatched"]) == 2


def test_malformed_final_and_refusal_are_not_reported_as_answers():
    malformed = run_assistant(
        config=TargetConfig(),
        context=context(),
        model=ToolFake(responses=[AIMessage(content="plain text")]),
        user_message="Hello",
    )
    assert malformed.status == "inconclusive"
    assert malformed.reason_code == "malformed_final_response"
    assert malformed.response is None
    refused = run_assistant(
        config=TargetConfig(),
        context=context(),
        model=ToolFake(responses=[final("I cannot do that.", "refusal")]),
        user_message="Hello",
    )
    assert refused.status == "refused"
    assert refused.response.display_text == "I cannot do that."
    unsupported = run_assistant(
        config=TargetConfig(),
        context=context(),
        model=ToolFake(responses=[final("Made-up citation", transaction_ids=["S-9999"])]),
        user_message="Show a transaction",
    )
    assert unsupported.status == "inconclusive"
    assert unsupported.reason_code == "unsupported_citation"


def test_unknown_and_forged_tool_calls_never_reach_repository():
    for response, reason in (
        (call("delete_account", {}), "unknown_tool"),
        (call("get_my_latest_transaction", {"customer_id": BOB_ID}), "tool_execution_failed"),
    ):
        run = run_assistant(
            config=TargetConfig(),
            context=context(),
            model=ToolFake(responses=[response]),
            user_message="Read data",
        )
        assert run.status == "error", (
            reason,
            run.reason_code,
            [event.payload for event in events_for(run) if event.name == "model.responded"],
        )
        assert run.reason_code == reason
        events = events_for(run)
        assert any(event.name == "tool.denied" for event in events)
        assert not any(event.name == "repository.read_completed" for event in events)
        assert not any(event.name == "context.prepared" for event in events)


def test_limits_and_provider_errors_terminate_without_scripted_fallback(monkeypatch):
    too_many = AIMessage(
        content="",
        tool_calls=[
            {"name": "get_my_latest_transaction", "args": {}, "id": f"call-{index}"}
            for index in range(5)
        ],
    )
    limited = run_assistant(
        config=TargetConfig(),
        context=context(),
        model=ToolFake(responses=[too_many]),
        user_message="Read data",
    )
    assert limited.status == "inconclusive"
    assert limited.reason_code == "tool_call_limit"
    assert limited.tool_calls == 0
    assert not any(event.name == "tool.requested" for event in events_for(limited))

    monkeypatch.setattr("app.runtime.MAX_MODEL_CALLS", 1)
    model = ToolFake(responses=[call("get_my_latest_transaction", {}), final()])
    model_limited = run_assistant(
        config=TargetConfig(), context=context(), model=model, user_message="Read data"
    )
    assert model_limited.status == "inconclusive"
    assert model_limited.reason_code == "model_call_limit"
    assert model_limited.model_calls == 1
    assert len(model.seen) == 1
    assert (
        len([event for event in events_for(model_limited) if event.name == "context.dispatched"])
        == 1
    )

    failed = run_assistant(
        config=TargetConfig(),
        context=context(),
        model=BrokenFake(responses=[final()]),
        user_message="Read data",
    )
    assert failed.status == "error"
    assert failed.reason_code == "model_call_failed"
    assert failed.response is None
    assert "provider-secret-detail" not in " ".join(
        event.model_dump_json() for event in events_for(failed)
    )
