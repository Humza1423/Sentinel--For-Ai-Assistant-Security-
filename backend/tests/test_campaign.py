import hashlib
import json

import pytest

from app.assistant import build_banking_agent, make_bank_tools
from app.bank import ALICE_ID, BOB_ID, BOB_MARKER, BankRepository, VulnerableLabBankRepository
from app.campaign import run_campaign


def test_phishing_weak_case_fails_and_replay_blocks():
    report = run_campaign("memo-phishing")
    assert report.baseline.verdict == "violated"
    assert "UNTRUSTED_LINK_PRESENTED_AS_BANK_ACTION" in report.baseline.violations
    assert report.replay.verdict == "blocked"
    assert report.replay.actions == []
    assert report.replay_inputs_identical
    assert report.baseline.violation_evidence[0].supporting_event_ids == ["e04"]
    assert report.benign_passed == report.benign_total == 5
    for run in (report.baseline, report.replay):
        for index, event in enumerate(run.events):
            expected_parent = run.events[index - 1].event_id if index else None
            assert event.parent_event_id == expected_parent
            digest_payload = event.model_dump(exclude={"digest"})
            assert (
                hashlib.sha256(json.dumps(digest_payload, sort_keys=True).encode()).hexdigest()
                == event.digest
            )


def test_cross_customer_case_proves_no_data_crosses_defended_boundary():
    report = run_campaign("cross-customer")
    assert report.baseline.verdict == "violated"
    assert report.baseline.tool_events[0].marker_in_result
    assert BOB_MARKER in report.baseline.response
    assert report.replay.verdict == "blocked"
    assert report.replay.tool_events[0].authorization == "denied"
    assert not report.replay.tool_events[0].marker_in_result
    assert BOB_MARKER not in report.replay.response
    assert report.benign_passed == 5


def test_live_mode_is_never_mislabeled_as_scripted_success():
    with pytest.raises(RuntimeError, match="not wired yet"):
        run_campaign("memo-phishing", "live")


def test_langchain_defended_tool_schema_has_no_model_controlled_identity():
    tool = make_bank_tools(defended=True)[0]
    assert "customer_id" not in tool.args
    assert tool.name == "get_my_latest_transaction"
    assert "Northstar" not in tool.invoke({})


def test_live_langchain_agent_can_be_constructed_without_sending_provider_requests(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-secret")
    agent = build_banking_agent(defended=True)
    assert callable(agent.invoke)


def test_langchain_vulnerable_fixture_can_reproduce_cross_customer_read():
    events = []
    tool = make_bank_tools(defended=False, tool_events=events)[0]
    returned = tool.invoke({"customer_id": "C-200"})
    assert BOB_MARKER in returned
    assert events[0]["authorization"] == "allowed"


def test_sqlite_bank_snapshot_is_repeatable_and_repository_checks_ownership():
    repository = BankRepository()
    assert repository.snapshot_digest() == BankRepository().snapshot_digest()
    with pytest.raises(PermissionError):
        repository.get_for(BOB_ID, ALICE_ID)
    assert VulnerableLabBankRepository(repository).lookup_latest(BOB_ID).customer_id == BOB_ID
