"""T04 boundaries: actual tools, session scope, lab isolation and evidence."""

import json
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.assistant import make_bank_tool_profile
from app.bank import ALICE_ID, BOB_ID, BOB_MARKER, BankRepository, SnapshotBankRepository
from app.evidence import EvidenceRecorder, read_events
from app.gateway import authorize_bank_read
from app.target_contracts import RequestContext, TargetConfig
from app.targets import resolve_target


def context(customer=ALICE_ID):
    return RequestContext(
        session_id="t04-session", authenticated_customer_id=customer, request_id=str(uuid4())
    )


def test_protected_profile_binds_identity_and_exposes_useful_read_tools():
    target = resolve_target(TargetConfig(), context=context())
    manifest = target.manifest()
    assert {tool.name for tool in target.bank_profile.tools} >= {
        "list_my_transactions",
        "get_my_transaction",
        "summarize_my_spending",
        "compare_my_spending",
    }
    for tool in manifest.tools:
        assert "customer_id" not in tool.input_schema.get("properties", {})
    listing = next(
        tool for tool in target.bank_profile.tools if tool.name == "list_my_transactions"
    )
    page = json.loads(listing.invoke({"limit": 20}))
    rows = page["records"]
    assert rows and all("customer_id" not in row for row in rows)
    assert page["currency"] == "CAD"
    assert len(rows) == 20
    assert page["matching_count"] == len(SnapshotBankRepository().transactions(context()))
    assert page["has_more"]
    total = next(tool for tool in target.bank_profile.tools if tool.name == "summarize_my_spending")
    output = json.loads(total.invoke({"start_date": "2026-10-20", "end_date": "2026-10-23"}))
    assert output["spent_cents"] >= 0


def test_trusted_context_wins_over_legacy_customer_parameter():
    legacy_events = []
    profile = make_bank_tool_profile(
        defended=True,
        context=context(BOB_ID),
        authenticated_customer_id=ALICE_ID,
        tool_events=legacy_events,
    )
    profile.tools[0].invoke({})
    assert legacy_events[0]["customer_id"] == BOB_ID


def test_forged_identity_is_rejected_before_snapshot_read(monkeypatch):
    recorder = EvidenceRecorder.start()
    target = resolve_target(TargetConfig(), context=context(), evidence=recorder)
    tool = next(tool for tool in target.bank_profile.tools if tool.name == "list_my_transactions")

    def forbidden(*args, **kwargs):
        pytest.fail("Malformed tool input must not read a snapshot")

    monkeypatch.setattr(SnapshotBankRepository, "__post_init__", forbidden)
    with pytest.raises(ValidationError):
        tool.invoke({"customer_id": BOB_ID})
    events = read_events(recorder.run_id).events
    assert [event.name for event in events][-2:] == ["tool.requested", "tool.denied"]
    assert not any(event.name.startswith("repository.read") for event in events)


def test_invalid_category_stops_before_snapshot_read(monkeypatch):
    recorder = EvidenceRecorder.start()
    target = resolve_target(TargetConfig(), context=context(), evidence=recorder)
    tool = next(tool for tool in target.bank_profile.tools if tool.name == "list_my_transactions")

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid category must not load a snapshot")

    monkeypatch.setattr(SnapshotBankRepository, "__post_init__", forbidden)
    with pytest.raises(ValidationError):
        tool.invoke({"category": "not-a-bank-category"})
    names = [event.name for event in read_events(recorder.run_id).events]
    assert names[-2:] == ["tool.requested", "tool.denied"]
    assert "repository.read_completed" not in names


def test_gateway_rejects_foreign_identity_without_repository_read():
    recorder = EvidenceRecorder.start()
    with (
        recorder.bind(),
        pytest.raises(PermissionError),
        authorize_bank_read(context(), profile="session_bound_v1", requested_customer_id=BOB_ID),
    ):
        pytest.fail("Denied scope must not reach repository")
    events = read_events(recorder.run_id).events
    assert [event.name for event in events] == ["authorization.decided"]
    assert events[0].payload["decision"] == "denied"
    assert events[0].payload["authenticated_customer_id"] == ALICE_ID
    assert events[0].payload["requested_customer_id"] == BOB_ID
    assert events[0].provenance == {"authenticated_customer_id": "system_trusted"}


def test_unknown_gateway_profile_fails_closed():
    recorder = EvidenceRecorder.start()
    with (
        recorder.bind(),
        pytest.raises(ValueError, match="Unknown bank tool profile"),
        authorize_bank_read(context(), profile="not_registered"),
    ):
        pytest.fail("Unknown profile must not execute")
    assert read_events(recorder.run_id).events == ()


def test_foreign_detail_probe_returns_no_data_and_no_successful_read():
    repository = SnapshotBankRepository()
    foreign_id = next(
        item.transaction_id
        for item in repository.snapshot.transactions
        if item.customer_id == BOB_ID
    )
    recorder = EvidenceRecorder.start()
    target = resolve_target(TargetConfig(), context=context(), evidence=recorder)
    tool = next(tool for tool in target.bank_profile.tools if tool.name == "get_my_transaction")
    assert tool.invoke({"transaction_id": foreign_id}) == "No matching transaction."
    events = read_events(recorder.run_id).events
    denied = [
        event
        for event in events
        if event.name == "authorization.decided" and event.actor == "repository"
    ]
    assert len(denied) == 1
    assert denied[0].payload["decision"] == "denied"
    assert denied[0].payload["reason_code"] == "transaction_not_owned_or_missing"
    assert denied[0].provenance["authenticated_customer_id"] == "system_trusted"
    assert not any(event.name == "repository.read_completed" for event in events)


def test_lab_profile_exposes_controlled_foreign_lookup_with_honest_manifest():
    target = resolve_target(TargetConfig(tool_profile="vulnerable_lookup_v1"), context=context())
    manifest = target.manifest()
    tool = next(
        tool for tool in target.bank_profile.tools if tool.name == "lookup_customer_transaction"
    )
    assert manifest.customer_access.identity_source == "model_argument"
    assert manifest.tools[0].model_controlled_arguments == ("customer_id",)
    assert manifest.tools[0].trusted_context_bindings == ()
    assert all(
        item.trusted_context_bindings == ("RequestContext.authenticated_customer_id",)
        for item in manifest.tools[1:]
    )
    assert BOB_MARKER in tool.invoke({"customer_id": BOB_ID})
    with pytest.raises(PermissionError):
        BankRepository().get_for(BOB_ID, ALICE_ID)


def test_lab_evidence_correlates_proposed_identity_with_executed_read():
    recorder = EvidenceRecorder.start()
    target = resolve_target(
        TargetConfig(tool_profile="vulnerable_lookup_v1"), context=context(), evidence=recorder
    )
    tool = target.bank_profile.tools[0]
    assert BOB_MARKER in tool.invoke({"customer_id": BOB_ID})
    events = read_events(recorder.run_id).events
    names = [event.name for event in events]
    assert names == [
        "target.resolved",
        "tool.requested",
        "arguments.validated",
        "authorization.decided",
        "tool.effective_arguments",
        "repository.read_completed",
        "tool.completed",
    ]
    requested, decision, effective, read = events[1], events[3], events[4], events[5]
    assert requested.payload["requested_arguments"]["customer_id"] == BOB_ID
    assert decision.payload["authenticated_customer_id"] == ALICE_ID
    assert decision.payload["requested_customer_id"] == BOB_ID
    assert effective.payload["effective_customer_id"] == BOB_ID
    assert read.payload["record_owners"] == [BOB_ID]
    assert "requested_arguments" not in requested.provenance
    assert decision.parent_event_id == requested.event_id
    assert effective.parent_event_id == decision.event_id
    assert read.parent_event_id == effective.event_id


def test_run_overlay_reaches_snapshot_tool_only_for_matching_run():
    repository = SnapshotBankRepository()
    row = repository.transactions(context(), limit=1)[0]
    repository.apply_memo_overlay(context(), "t04-run", row.transaction_id, "attacker memo")
    target = resolve_target(
        TargetConfig(tool_profile="vulnerable_lookup_v1"), context=context(), run_id="t04-run"
    )
    listing = next(
        tool for tool in target.bank_profile.tools if tool.name == "list_my_transactions"
    )
    records = json.loads(listing.invoke({"start_date": date(2026, 10, 23).isoformat(), "limit": 2}))
    assert records["records"][0]["memo"] == {
        "text": "attacker memo",
        "provenance": "external_untrusted",
    }
    clean = resolve_target(
        TargetConfig(tool_profile="vulnerable_lookup_v1"), context=context(), run_id="other-run"
    )
    clean_listing = next(
        tool for tool in clean.bank_profile.tools if tool.name == "list_my_transactions"
    )
    assert (
        json.loads(clean_listing.invoke({"limit": 1}))["records"][0]["memo"]["text"]
        != "attacker memo"
    )
