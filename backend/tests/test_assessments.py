from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import assessments
from app.chat import create_session
from app.main import app
from app.target_contracts import TargetConfig


def setup():
    owner = str(uuid4())
    sid = create_session(TargetConfig(tool_profile="vulnerable_lookup_v1"), owner)["session_id"]
    return sid, owner


def test_completed_report_is_repeatable_and_owner_scoped():
    sid, owner = setup()
    request = str(uuid4())
    aid, fresh = assessments.create_assessment(sid, owner, request)
    assert fresh
    assessments.execute_assessment(aid)
    state = assessments.read_assessment(aid, owner)
    assert state["status"] == "complete"
    assert len(state["report"]["benign"]) == 5
    assert state["report"]["mode"] == "fixture_execution"
    assert assessments.create_assessment(sid, owner, request) == (aid, False)
    before = state["events"]
    assessments.execute_assessment(aid)
    assert assessments.read_assessment(aid, owner)["events"] == before
    with pytest.raises(LookupError):
        assessments.read_assessment(aid, "another-owner")
    assert not assessments.read_assessment(aid, owner, before[-1]["sequence"])["events"]


def test_queue_cancel_and_restart_do_not_rerun_work():
    sid, owner = setup()
    aid, _ = assessments.create_assessment(sid, owner, str(uuid4()))
    with pytest.raises(ValueError, match="already running"):
        assessments.create_assessment(sid, owner, str(uuid4()))
    assessments.cancel_assessment(aid, owner)
    assessments.execute_assessment(aid)
    assert assessments.read_assessment(aid, owner)["status"] == "cancelled"
    another, _ = assessments.create_assessment(sid, owner, str(uuid4()))
    assessments.recover_assessments()
    assessments.execute_assessment(another)
    assert assessments.read_assessment(another, owner)["status"] == "interrupted"


def test_cancellation_between_model_calls_keeps_partial_trace(monkeypatch):
    from app.fixture_model import BankingFixtureModel

    sid, owner = setup()
    aid, _ = assessments.create_assessment(sid, owner, str(uuid4()))
    original = BankingFixtureModel.invoke

    def cancel_after_first(self, *args, **kwargs):
        response = original(self, *args, **kwargs)
        assessments.cancel_assessment(aid, owner)
        return response

    monkeypatch.setattr(BankingFixtureModel, "invoke", cancel_after_first)
    assessments.execute_assessment(aid)
    state = assessments.read_assessment(aid, owner)
    assert state["status"] == "cancelled"
    assert state["report"] is None
    assert any(e["type"] == "reference_control" for e in state["events"])


def test_http_report_events_and_bad_owner():
    sid, owner = setup()
    with TestClient(app) as client:
        client.cookies.set("sentinel_owner", owner)
        response = client.post(
            "/api/v2/assessments", json={"session_id": sid, "request_id": str(uuid4())}
        )
        assert response.status_code == 200
        aid = response.json()["assessment_id"]
        url = f"/api/v2/assessments/{aid}"
        assert client.get(url).json()["status"] == "complete"
        assert client.get(url + "/report").json()["benign"]
        events = client.get(url + "/events")
        assert "text/event-stream" in events.headers["content-type"]
        assert "event: progress" in events.text
        sequence = client.get(url).json()["events"][-1]["sequence"]
        assert not client.get(url + "/events", headers={"Last-Event-ID": str(sequence)}).text
        client.cookies.set("sentinel_owner", "wrong")
        assert client.get(url).status_code == 404
