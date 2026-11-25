from uuid import UUID, uuid4

import pytest

from app.chat import create_session, submit_message
from app.input_comparison import compare_chat_inputs
from app.target_contracts import TargetConfig


def turn(owner, message="Show my latest transfer", session=None):
    sid = session or create_session(TargetConfig(), owner)["session_id"]
    result = submit_message(sid, owner, str(uuid4()), message)
    return sid, UUID(str(result["run_id"]))


def test_independent_equivalent_inputs_and_followup():
    sid, left = turn("tester")
    _, right = turn("tester")
    same = compare_chat_inputs(left, right, owner="tester")
    assert same.status == "same"
    assert all(f.left_event_ids and f.right_event_ids for f in same.fields)
    _, followup = turn("tester", session=sid)
    diff = compare_chat_inputs(left, followup, owner="tester")
    assert diff.status == "different"
    assert next(f for f in diff.fields if f.field == "first_dispatch").status == "different"


def test_private_turns_and_distinct_runs():
    _, left = turn("owner-a")
    _, right = turn("owner-b")
    with pytest.raises(LookupError):
        compare_chat_inputs(left, right, owner="owner-a")
    with pytest.raises(ValueError):
        compare_chat_inputs(left, left, owner="owner-a")
