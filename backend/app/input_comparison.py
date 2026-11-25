"""Compare recorded inputs to two completed ordinary chat turns."""

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select

from .chat import require_session
from .evidence import EvidenceError
from .observed_scoring import read_run_trace
from .store import ChatTurnRow, Session

Match = Literal["same", "different", "unknown"]
_FIELDS = ("execution_mode", "customer", "target", "source", "first_dispatch", "snapshot")


class FieldComparison(BaseModel):
    field: str
    status: Match
    left_event_ids: list[UUID]
    right_event_ids: list[UUID]


class InputComparison(BaseModel):
    left_run_id: UUID
    right_run_id: UUID
    status: Match
    fields: list[FieldComparison]


def _digest(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value)


def _observations(run_id, turn):
    try:
        events, origin = read_run_trace(run_id)
    except EvidenceError:
        return {}
    requests = [e for e in events if e.name == "request.received"]
    outputs = [e for e in events if e.name == "assistant.output"]
    if len(requests) != 1 or len(outputs) != 1:
        return {}
    req, output = requests[0], outputs[0]
    payload = req.payload
    if (
        payload.get("session_id") != turn.session_id
        or payload.get("request_id") != turn.request_id
        or payload.get("memo_overlay_run_id") is not None
        or output.payload.get("status") not in ("answered", "refused")
        or req.sequence >= output.sequence
    ):
        return {}
    ids = [req.event_id]
    observed = {"execution_mode": (origin, ids)}
    for field, key in (("customer", "authenticated_customer_id"), ("target", "target_digest")):
        value = payload.get(key)
        if (
            req.provenance.get(key) == "system_trusted"
            and isinstance(value, str)
            and value
            and (field != "target" or _digest(value))
        ):
            observed[field] = (value, ids)
    receipt = payload.get("source_receipt")
    if (
        req.provenance.get("source_receipt") == "system_trusted"
        and isinstance(receipt, dict)
        and receipt.get("status") == "verified"
        and _digest(receipt.get("digest"))
    ):
        observed["source"] = (receipt["digest"], ids)

    current = [e for e in events if req.sequence < e.sequence < output.sequence]
    calls = [
        e for e in current if e.name == "model.requested" and e.payload.get("call_number") == 1
    ]
    if len(calls) == 1:
        call = calls[0]
        dispatched = [
            e
            for e in current
            if e.name == "context.dispatched"
            and (
                (
                    origin == "live_execution"
                    and e.parent_event_id == call.event_id
                    and e.sequence > call.sequence
                )
                or (
                    origin == "fixture_execution"
                    and call.parent_event_id == e.event_id
                    and e.parent_event_id == req.event_id
                    and e.sequence < call.sequence
                )
            )
        ]
        if len(dispatched) == 1:
            event = dispatched[0]
            messages = event.payload.get("message_digests")
            if (
                isinstance(messages, list)
                and len(messages) >= 2
                and len(messages) == event.payload.get("message_count")
                and all(_digest(v) for v in messages)
            ):
                observed["first_dispatch"] = (messages, [event.event_id, call.event_id])
    reads = [e for e in current if e.name == "repository.read_completed"]
    digests = [e.payload.get("snapshot_digest") for e in reads]
    if digests and all(_digest(d) and d == digests[0] for d in digests):
        observed["snapshot"] = (digests[0], [e.event_id for e in reads])
    return observed


def compare_chat_inputs(
    left_run_id: UUID, right_run_id: UUID, *, owner: str | None
) -> InputComparison:
    if left_run_id == right_run_id:
        raise ValueError("Choose two different chat runs")
    observations = []
    with Session() as db:
        for run_id in (left_run_id, right_run_id):
            turn = db.scalar(select(ChatTurnRow).where(ChatTurnRow.run_id == str(run_id)))
            if turn is None:
                raise LookupError("Chat run not found")
            require_session(db, turn.session_id, owner)
            observations.append(_observations(run_id, turn))
    left, right = observations
    fields = []
    for field in _FIELDS:
        a, a_ids = left.get(field, (None, []))
        b, b_ids = right.get(field, (None, []))
        status = "unknown" if a is None or b is None else "same" if a == b else "different"
        fields.append(
            FieldComparison(field=field, status=status, left_event_ids=a_ids, right_event_ids=b_ids)
        )
    states = {f.status for f in fields}
    status = "different" if "different" in states else "unknown" if "unknown" in states else "same"
    return InputComparison(
        left_run_id=left_run_id, right_run_id=right_run_id, status=status, fields=fields
    )
