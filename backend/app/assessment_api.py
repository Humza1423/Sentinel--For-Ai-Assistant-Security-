"""HTTP lifecycle for explicitly labelled local banking evaluations."""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Cookie, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from . import assessments

router = APIRouter(prefix="/api/v2/assessments")


class StartAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: UUID
    request_id: UUID


def owned(assessment_id, owner, after=0):
    try:
        return assessments.read_assessment(str(assessment_id), owner, after)
    except LookupError:
        raise HTTPException(404, "Assessment unavailable") from None


@router.post("")
def create(
    body: StartAssessment,
    background: BackgroundTasks,
    sentinel_owner: str | None = Cookie(default=None),
):
    try:
        aid, fresh = assessments.create_assessment(
            str(body.session_id), sentinel_owner, str(body.request_id)
        )
    except LookupError:
        raise HTTPException(404, "Session unavailable") from None
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if fresh:
        background.add_task(assessments.execute_assessment, aid)
    return owned(aid, sentinel_owner)


@router.get("/{assessment_id}")
def get(assessment_id: UUID, sentinel_owner: str | None = Cookie(default=None)):
    return owned(assessment_id, sentinel_owner)


@router.post("/{assessment_id}/cancel")
def cancel(assessment_id: UUID, sentinel_owner: str | None = Cookie(default=None)):
    owned(assessment_id, sentinel_owner)
    assessments.cancel_assessment(str(assessment_id), sentinel_owner)
    return owned(assessment_id, sentinel_owner)


@router.get("/{assessment_id}/report")
def report(assessment_id: UUID, sentinel_owner: str | None = Cookie(default=None)):
    state = owned(assessment_id, sentinel_owner)
    if state["report"] is None:
        raise HTTPException(409, "Completed report unavailable")
    return state["report"]


@router.get("/{assessment_id}/events")
def events(
    assessment_id: UUID,
    after: int = Query(default=0, ge=0),
    last_event_id: Annotated[int | None, Header(ge=0)] = None,
    sentinel_owner: str | None = Cookie(default=None),
):
    # Finite persisted SSE page. Reconnection resumes by sequence, with no new work.
    state = owned(assessment_id, sentinel_owner, max(after, last_event_id or 0))

    def stream():
        for event in state["events"]:
            yield f"id: {event['sequence']}\nevent: progress\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
