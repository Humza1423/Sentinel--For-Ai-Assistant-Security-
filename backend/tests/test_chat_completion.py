"""T09 release regressions, with independent fixture amounts and no provider calls."""

import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from test_runtime import ToolFake, call, final

from app.bank import ALICE_ID, SnapshotBankRepository
from app.chat import create_session, run_events, submit_message
from app.fixture_model import BankingFixtureModel
from app.runtime import run_assistant
from app.runtime_context import assistant_instructions
from app.target_contracts import RequestContext, TargetConfig
from app.targets import resolve_target


def context():
    return RequestContext(
        session_id="completion", authenticated_customer_id=ALICE_ID, request_id=str(uuid4())
    )


class AuditHeavyFixture(BankingFixtureModel):
    def _generate(self, messages, **kwargs):
        result = super()._generate(messages, **kwargs)
        result.generations[0].message.response_metadata["audit_only"] = "x" * 20000
        return result


def test_ten_turns_with_audit_metadata_and_rollover_preserve_pairs():
    owner = str(uuid4())
    session = create_session(TargetConfig(tool_profile="vulnerable_lookup_v1"), owner)
    for index in range(10):
        question = ["Show spending", "Show groceries spending", "Exclude groceries"][index % 3]
        result = submit_message(
            session["session_id"], owner, str(uuid4()), question, model_factory=AuditHeavyFixture
        )
        assert result["status"] == "answered"
        assert result["retained_turns"] <= 5
        if question == "Exclude groceries":
            assert "649.00" in result["response"]["display_text"]
        events = run_events(result["run_id"])
        prepared = {str(e.event_id) for e in events if e.name == "context.prepared"}
        for event in events:
            if event.name == "context.dispatched":
                for reference in event.payload["tool_results"]:
                    assert (
                        reference.get("source_run_id") or reference["prepared_event_id"] in prepared
                    )
    assert result["dropped_turns"] >= 4


def test_filters_pagination_and_aggregates_use_same_scoped_bank():
    target = resolve_target(TargetConfig(), context=context())
    tools = {t.name: t for t in target.bank_profile.tools}
    args = {"start_date": "2026-10-01", "end_date": "2026-10-23"}
    result = json.loads(tools["summarize_my_spending"].invoke({**args, "merchant": "mApLe"}))
    assert result["spent_cents"] == 8500
    assert result["start_date"] == "2026-10-01"
    assert (
        json.loads(
            tools["summarize_my_spending"].invoke({**args, "exclude_categories": ["groceries"]})
        )["spent_cents"]
        == 12980
    )
    page = json.loads(
        tools["list_my_transactions"].invoke(
            {**args, "category": "groceries", "min_amount_cents": 4001, "limit": 1}
        )
    )
    assert page["matching_count"] == 2 and page["has_more"]
    assert page["records"][0]["transaction_id"] == "S-0001"
    second = json.loads(
        tools["list_my_transactions"].invoke(
            {**args, "category": "groceries", "min_amount_cents": 4001, "limit": 1, "offset": 1}
        )
    )
    assert second["records"][0]["transaction_id"] == "S-0017" and not second["has_more"]
    assert all(r["amount_cents"] < 0 for r in page["records"])
    repo = SnapshotBankRepository()
    transit = repo.transaction_page(context(), merchant="Metro Transit")[0]
    assert len(transit) == 10
    assert all(row.customer_id == ALICE_ID for row in transit)


@pytest.mark.parametrize(
    "invalid", [{"category": "pizza"}, {"start_date": "2026-10-23", "end_date": "2026-10-01"}]
)
def test_one_argument_correction_executes_real_tool(invalid):
    model = ToolFake(
        responses=[
            call("list_my_transactions", invalid, "bad"),
            call("list_my_transactions", {"limit": 1}, "corrected"),
            final(transaction_ids=["S-0001"]),
        ]
    )
    run = run_assistant(
        config=TargetConfig(), context=context(), model=model, user_message="Latest transaction"
    )
    assert run.status == "answered" and run.tool_calls == 2
    assert isinstance(model.seen[1][-1], ToolMessage)
    assert json.loads(model.seen[1][-1].content)["error"] == "invalid_arguments"
    names = [e.name for e in run_events(str(run.run_id))]
    assert names.count("tool.correction_requested") == 1
    assert names.count("repository.read_completed") == 1


def test_repeated_invalid_arguments_stop_and_no_repository_reads():
    model = ToolFake(
        responses=[
            call("list_my_transactions", {"category": "pizza"}, "bad1"),
            call("list_my_transactions", {"category": "pizza"}, "bad2"),
        ]
    )
    run = run_assistant(
        config=TargetConfig(), context=context(), model=model, user_message="Show transactions"
    )
    assert run.status == "error" and run.reason_code == "invalid_arguments_limit"
    assert run.tool_calls == 2
    assert not any(e.name == "repository.read_completed" for e in run_events(str(run.run_id)))


def test_trusted_context_has_exact_dates_and_scope():
    snapshot = SnapshotBankRepository().snapshot
    prompt = assistant_instructions(TargetConfig())
    assert min(r.date for r in snapshot.transactions).isoformat() in prompt
    assert max(r.date for r in snapshot.transactions).isoformat() in prompt
    assert "For unrelated tasks" in prompt
    assert "month-to-date" in prompt


def test_wire_sizing_excludes_audit_metadata_but_preserves_content(monkeypatch):
    from app.evidence import EvidenceRecorder
    from app.live_model import MeteredOpenAIModel

    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    model = MeteredOpenAIModel(
        TargetConfig().model, EvidenceRecorder.start(origin="live_execution")
    )
    try:
        model.bind_tools([])
        message = AIMessage(content="Hello", response_metadata={"audit": "x" * 50000})
        size = model.input_size([message])
        assert size < 12000
        assert size == model.input_size([AIMessage(content="Hello")])
    finally:
        model.close()


def test_changed_target_requires_new_session_without_losing_history():
    from app.chat import ChatError, get_session
    from app.store import ChatSessionRow, Session

    owner = str(uuid4())
    original = create_session(TargetConfig(), owner)
    sid = original["session_id"]
    assert not original["requires_new_conversation"]
    submit_message(sid, owner, str(uuid4()), "Show spending")
    with Session.begin() as db:
        db.get(ChatSessionRow, sid).target_digest = "old-version"
    restored = get_session(sid, owner)
    assert restored["requires_new_conversation"] and len(restored["turns"]) == 1
    with pytest.raises(ChatError, match="create a new session"):
        submit_message(sid, owner, str(uuid4()), "Show spending")
