import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, text, update
from sqlalchemy.exc import IntegrityError, OperationalError

from app.evidence import (
    EventDraft,
    EvidenceError,
    EvidenceRecorder,
    Redactor,
    RunEvent,
    UnknownRunError,
    emit,
    payload_digest,
    read_events,
)
from app.main import app
from app.store import ObservedEventRow, Session


def test_empty_run_and_ordered_paginated_retrieval():
    attempt_id = uuid4()
    recorder = EvidenceRecorder.start(attempt_id=attempt_id)
    assert read_events(recorder.run_id).events == ()
    events = [recorder.append("request.received", "application", {"number": n}) for n in range(4)]
    assert [e.sequence for e in events] == [1, 2, 3, 4]
    assert all(
        e.attempt_id == attempt_id and e.timestamp.utcoffset() == timedelta(0) for e in events
    )
    page = read_events(recorder.run_id, limit=2)
    assert page.events == tuple(events[:2])
    assert page.has_more and page.next_after_sequence == 2
    page = read_events(recorder.run_id, after_sequence=page.next_after_sequence, limit=2)
    assert page.events == tuple(events[2:])
    assert not page.has_more
    assert len({e.event_id for e in events}) == 4


def test_atomic_sequence_allocation_across_recorder_instances():
    original = EvidenceRecorder.start()

    def append(n):
        return EvidenceRecorder(original.run_id).append("request.received", "application", {"n": n})

    with ThreadPoolExecutor(max_workers=4) as executor:
        events = list(executor.map(append, range(24)))
    assert sorted(e.sequence for e in events) == list(range(1, 25))
    assert [e.sequence for e in read_events(original.run_id).events] == list(range(1, 25))
    assert len({e.event_id for e in events}) == 24
    another = EvidenceRecorder.start().append("request.received", "application", {})
    assert another.event_id not in {e.event_id for e in events}


def test_canonical_sanitized_digest_is_stable_without_mutating_input():
    original = {"b": 2, "nested": {"API_KEY": "synthetic-secret", "a": "café"}}
    redactor = Redactor()
    first = redactor.sanitize(original)
    second = redactor.sanitize({"nested": {"a": "café", "API_KEY": "different-secret"}, "b": 2})
    assert payload_digest(first) == payload_digest(second)
    assert original["nested"]["API_KEY"] == "synthetic-secret"
    recorder = EvidenceRecorder.start()
    event = recorder.append("request.received", "application", original)
    assert event.payload_digest == payload_digest(first)
    event.payload["b"] = 99
    assert read_events(recorder.run_id).events[0].payload["b"] == 2


def test_parent_validation_and_transaction_rollback():
    recorder = EvidenceRecorder.start()
    parent = recorder.append("tool.requested", "tool", {})
    child = recorder.append("arguments.validated", "tool", {}, parent_event_id=parent.event_id)
    assert child.parent_event_id == parent.event_id
    foreign = EvidenceRecorder.start().append("tool.requested", "tool", {})
    for invalid in (foreign.event_id, uuid4()):
        with pytest.raises(ValueError, match="earlier event"):
            recorder.append("tool.completed", "tool", {}, parent_event_id=invalid)
    assert recorder.append("tool.completed", "tool", {}).sequence == 3


@pytest.mark.parametrize(
    "change",
    [
        {"name": "invented.event"},
        {"actor": "unknown"},
        {"extra": True},
        {"provenance": {"memo": "trusted_because_model_said_so"}},
        {"parent_event_id": "not-a-uuid"},
    ],
)
def test_draft_contract_rejects_unknown_or_forged_fields(change):
    with pytest.raises(ValidationError):
        EventDraft(**({"name": "tool.requested", "actor": "tool", "payload": {}} | change))


@pytest.mark.parametrize(
    "payload",
    [
        {"n": float("nan")},
        {"n": float("inf")},
        {"n": object()},
        {1: "value"},
        {"n": b"bytes"},
        {"n": "x" * 65537},
    ],
)
def test_non_json_and_oversized_payloads_fail_without_persistence(payload):
    recorder = EvidenceRecorder.start()
    with pytest.raises((ValueError, TypeError)):
        recorder.append("request.received", "application", payload)
    assert read_events(recorder.run_id).events == ()


def test_event_contract_rejects_naive_and_non_utc_timestamps():
    event = EvidenceRecorder.start().append("request.received", "application", {})
    for timestamp in (datetime.now(), datetime.now(timezone(timedelta(hours=1)))):
        with pytest.raises(ValidationError):
            RunEvent.model_validate(event.model_dump() | {"timestamp": timestamp})
    assert RunEvent.model_validate(event.model_dump() | {"timestamp": datetime.now(UTC)})


def test_redaction_precedes_persistence_and_preserves_provenance(monkeypatch):
    known = "synthetic-known-provider-secret"
    patterned = "sk-proj-" + "a" * 40
    monkeypatch.setenv("OPENAI_API_KEY", known)
    recorder = EvidenceRecorder.start(
        redactor=Redactor(
            sensitive_fields=("customer.ssn", "private_note"),
            secret_values=(known,),
        )
    )
    event = recorder.append(
        "tool.requested",
        "tool",
        {
            "OPENAI_API_KEY": known,
            "headers": {"Authorization": "Bearer opaque-secret", "x-api-key": "opaque-value"},
            "nested": [{"access_token": "opaque-access", "refresh_token": "opaque-refresh"}],
            "customer": {"ssn": "synthetic-sensitive-field", "name": "Alice"},
            "private_note": "custom-sensitive-note",
            "message": f"key {known}; key {patterned}; Bearer opaque-header; OPENAI_API_KEY=opaque-env",
            "token_count": 42,
        },
        provenance={"message": "external_untrusted", "customer": "bank_record"},
    )
    with Session() as session:
        persisted = session.get(ObservedEventRow, str(event.event_id)).event_json
    for secret in (
        known,
        patterned,
        "opaque-secret",
        "opaque-value",
        "opaque-access",
        "opaque-refresh",
        "synthetic-sensitive-field",
        "custom-sensitive-note",
        "opaque-header",
        "opaque-env",
    ):
        assert secret not in persisted
    observed = read_events(recorder.run_id).events[0]
    assert observed.provenance == {"message": "external_untrusted", "customer": "bank_record"}
    assert observed.payload["token_count"] == 42
    assert observed.payload["customer"]["name"] == "Alice"
    assert observed.payload_digest == payload_digest(observed.payload)


def test_default_redactor_captures_key_value_without_exposing_it(monkeypatch):
    secret = "synthetic-environment-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    recorder = EvidenceRecorder.start()
    event = recorder.append("request.received", "application", {"text": f"accidental {secret}"})
    assert secret not in event.model_dump_json()
    assert secret not in repr(recorder)


def test_custom_field_redaction_cannot_disable_environment_key_redaction(monkeypatch):
    secret = "synthetic-environment-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    recorder = EvidenceRecorder.start(redactor=Redactor(sensitive_fields=("ssn",)))
    event = recorder.append(
        "request.received",
        "application",
        {
            "text": secret,
            secret: "as a key",
            "ssn": "synthetic-ssn",
        },
    )
    assert secret not in event.model_dump_json()
    assert event.payload["ssn"] == "[REDACTED]"


def test_sensitive_field_provenance_is_preserved_while_its_value_is_redacted():
    recorder = EvidenceRecorder.start()
    event = recorder.append(
        "request.received",
        "application",
        {"Authorization": "opaque"},
        provenance={"Authorization": "external_untrusted"},
    )
    assert event.payload["Authorization"] == "[REDACTED]"
    assert event.provenance == {"Authorization": "external_untrusted"}


@pytest.mark.parametrize(
    "statement",
    [
        lambda event_id: (
            update(ObservedEventRow)
            .where(ObservedEventRow.event_id == event_id)
            .values(event_json="{}")
        ),
        lambda event_id: delete(ObservedEventRow).where(ObservedEventRow.event_id == event_id),
    ],
)
def test_normal_sql_update_and_delete_are_rejected(statement):
    recorder = EvidenceRecorder.start()
    event = recorder.append("request.received", "application", {})
    with pytest.raises(IntegrityError, match="append-only"), Session.begin() as session:
        session.execute(statement(str(event.event_id)))
    assert read_events(recorder.run_id).events == (event,)


def test_payload_integrity_is_checked_on_read():
    recorder = EvidenceRecorder.start()
    event = recorder.append("request.received", "application", {})
    # Simulate a privileged actor bypassing the recorder, not a supported write path.
    corrupted = event.model_dump(mode="json") | {"event_id": str(uuid4()), "sequence": 2}
    corrupted["payload"] = {"changed": True}
    with Session.begin() as session:
        session.add(
            ObservedEventRow(
                event_id=corrupted["event_id"],
                run_id=str(recorder.run_id),
                sequence=2,
                parent_event_id=None,
                event_json=json.dumps(corrupted),
            )
        )
    with pytest.raises(EvidenceError, match="integrity"):
        read_events(recorder.run_id)


def test_missing_runs_and_invalid_page_bounds():
    with pytest.raises(UnknownRunError):
        read_events(uuid4())
    with pytest.raises(UnknownRunError):
        EvidenceRecorder(uuid4()).append("tool.requested", "tool", {})
    for arguments in ({"after_sequence": -1}, {"limit": 0}, {"limit": 1001}):
        with pytest.raises(ValueError):
            read_events(uuid4(), **arguments)


def test_recording_failure_has_a_safe_error_message():
    class BrokenStore:
        @staticmethod
        def begin():
            raise OperationalError("synthetic-sensitive-error", None, None)

    with pytest.raises(EvidenceError, match="Could not start evidence run") as error:
        EvidenceRecorder.start(session_factory=BrokenStore)
    assert "synthetic-sensitive-error" not in str(error.value)


def test_call_local_context_is_reset_and_isolated_between_async_tasks():
    first, second = EvidenceRecorder.start(), EvidenceRecorder.start()

    async def record(recorder, number):
        with recorder.bind():
            await asyncio.sleep(0)
            emit("tool.requested", "tool", {"number": number})

    async def both():
        await asyncio.gather(record(first, 1), record(second, 2))

    asyncio.run(both())
    assert emit("tool.completed", "tool", {}) is None
    assert read_events(first.run_id).events[0].payload == {"number": 1}
    assert read_events(second.run_id).events[0].payload == {"number": 2}


def test_read_only_api_pagination_unknown_run_and_no_mutation_routes():
    recorder = EvidenceRecorder.start()
    for n in range(3):
        recorder.append("request.received", "application", {"n": n})
    with TestClient(app) as client:
        path = f"/api/v2/runs/{recorder.run_id}/events"
        response = client.get(path, params={"limit": 2})
        assert response.status_code == 200
        assert [e["sequence"] for e in response.json()["events"]] == [1, 2]
        assert response.json()["has_more"]
        assert client.get(path, params={"after_sequence": 2}).json()["events"][0]["sequence"] == 3
        assert client.get(path, params={"after_sequence": -1}).status_code == 422
        assert client.get(f"/api/v2/runs/{uuid4()}/events").status_code == 404
        assert client.post(path, json={}).status_code == 405
        assert client.patch(path, json={}).status_code == 405
        assert client.delete(path).status_code == 405
        assert client.get(path).json()["origin"] == "direct_execution"


def test_failed_storage_reads_are_not_success_responses(monkeypatch):
    def failed(*args, **kwargs):
        raise EvidenceError("unsafe internal details")

    monkeypatch.setattr("app.main.read_events", failed)
    with TestClient(app) as client:
        response = client.get(f"/api/v2/runs/{uuid4()}/events")
    assert response.status_code == 503
    assert "unsafe internal details" not in response.text


def test_no_fake_future_agent_events_are_automatically_emitted():
    recorder = EvidenceRecorder.start()
    assert read_events(recorder.run_id).events == ()
    # Contract support alone is not an observation that an agent has run.
    assert EventDraft(name="defense.proposed", actor="defense", payload={})


def test_database_constraints_prevent_duplicate_sequence():
    recorder = EvidenceRecorder.start()
    event = recorder.append("request.received", "application", {})
    with pytest.raises(IntegrityError), Session.begin() as session:
        session.execute(
            text(
                "INSERT INTO observed_events (event_id, run_id, sequence, event_json) "
                "VALUES (:event_id, :run_id, 1, :event_json)"
            ),
            {
                "event_id": str(uuid4()),
                "run_id": str(recorder.run_id),
                "event_json": event.model_dump_json(),
            },
        )
