from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal
from uuid import UUID, uuid4

from fastapi import Cookie, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .assessment_api import router as assessment_router
from .assessments import recover_assessments
from .bank import ALICE_ID
from .budget import UsageBroker, estimate
from .campaign import run_campaign
from .chat import recover_interrupted, require_session
from .chat_api import router as chat_router
from .contracts import CampaignRequest
from .evidence import EventPage, EvidenceError, EvidenceRecorder, UnknownRunError, read_events
from .input_comparison import InputComparison, compare_chat_inputs
from .investigation import Investigation, investigate_run, recorded_assessment
from .live_model import MeteredOpenAIModel
from .remediation import RepairProposal, propose_repair
from .scenarios import SCENARIOS
from .settings import load_external_env_file
from .store import ChatTurnRow, Session, get_events, get_report, save_report
from .target_contracts import RequestContext, TargetConfig, TargetManifest, TargetModelConfig
from .targets import resolve_target

load_external_env_file()


@asynccontextmanager
async def lifespan(app):
    recover_interrupted()
    recover_assessments()
    yield


app = FastAPI(
    title="Banking Agent Security Workbench",
    description="Synthetic, local attack/repair/replay lab for tool-using banking assistants.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(chat_router)
app.include_router(assessment_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=True,
)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "default_mode": "scripted",
        "live_agent_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/v2/usage")
def usage_summary():
    from .live_model import live_status

    return {
        **UsageBroker().summary(),
        "call_estimate": estimate(),
        "live_chat": live_status(),
        "live_adapter_available": True,
    }


@app.post("/api/v2/targets/resolve", response_model=TargetManifest)
def resolve_target_configuration(config: TargetConfig):
    """Preview registered capabilities; does not save a target or execute a model/tool."""
    context = RequestContext(
        session_id="synthetic-target-preview",
        authenticated_customer_id=ALICE_ID,
        request_id=str(uuid4()),
    )
    try:
        return resolve_target(config, context=context).manifest()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def require_run_access(run_id, sentinel_owner):
    with Session() as db:
        turn = db.scalar(select(ChatTurnRow).where(ChatTurnRow.run_id == str(run_id)))
        if turn is not None:
            try:
                require_session(db, turn.session_id, sentinel_owner)
            except LookupError as exc:
                raise HTTPException(404, "Run not found") from exc


@app.get("/api/v2/runs/{run_id}/events", response_model=EventPage)
def observed_run_events(
    run_id: UUID,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=1000),
    sentinel_owner: str | None = Cookie(default=None),
):
    require_run_access(run_id, sentinel_owner)
    try:
        return read_events(run_id, after_sequence=after_sequence, limit=limit)
    except UnknownRunError as exc:
        raise HTTPException(404, str(exc)) from exc
    except EvidenceError:
        raise HTTPException(503, "Evidence is unavailable or incomplete") from None


@app.get("/api/v2/runs/{run_id}/input-comparison/{other_run_id}", response_model=InputComparison)
def compare_recorded_chat_inputs(
    run_id: UUID, other_run_id: UUID, sentinel_owner: str | None = Cookie(default=None)
):
    try:
        return compare_chat_inputs(run_id, other_run_id, owner=sentinel_owner)
    except LookupError:
        raise HTTPException(404, "Chat run unavailable") from None
    except ValueError:
        raise HTTPException(422, "Choose two different chat runs") from None
    except EvidenceError:
        raise HTTPException(503, "Run evidence unavailable") from None


@app.post("/api/v2/runs/{run_id}/investigation", response_model=Investigation)
def investigate_observed_run(
    run_id: UUID,
    mode: Literal["offline", "live"] = "offline",
    sentinel_owner: str | None = Cookie(default=None),
):
    require_run_access(run_id, sentinel_owner)
    if mode == "offline":
        return investigate_run(run_id)
    model = create_analysis_model(run_id)
    try:
        return investigate_run(run_id, model=model)
    finally:
        model.close()


def create_analysis_model(run_id: UUID):
    assessment_id = recorded_assessment(run_id)
    if assessment_id is None:
        raise HTTPException(409, "Live analysis requires a run with an existing assessment budget")
    try:
        return MeteredOpenAIModel(
            TargetModelConfig(), EvidenceRecorder(run_id), assessment_id=assessment_id
        )
    except ValueError:
        raise HTTPException(503, "Analysis provider unavailable") from None


@app.post(
    "/api/v2/runs/{run_id}/investigations/{investigation_event_id}/repair-proposal",
    response_model=RepairProposal,
)
def request_repair_proposal(
    run_id: UUID,
    investigation_event_id: UUID,
    mode: Literal["offline", "live"] = "offline",
    sentinel_owner: str | None = Cookie(default=None),
):
    require_run_access(run_id, sentinel_owner)
    if mode == "offline":
        return propose_repair(run_id, investigation_event_id)
    model = create_analysis_model(run_id)
    try:
        return propose_repair(run_id, investigation_event_id, model=model)
    finally:
        model.close()


@app.get("/api/scenarios")
def scenarios():
    return [scenario.model_dump() for scenario in SCENARIOS.values()]


@app.get("/api/scenarios/{scenario_id}")
def scenario_detail(scenario_id: str):
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise HTTPException(404, "Unknown scenario")
    return scenario.model_dump()


@app.post("/api/campaigns")
def create_campaign(request: CampaignRequest):
    if request.scenario_id not in SCENARIOS:
        raise HTTPException(404, "Unknown scenario")
    try:
        report = run_campaign(request.scenario_id, request.mode)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    payload = report.model_dump(mode="json")
    save_report(payload)
    return payload


@app.get("/api/campaigns/{campaign_id}")
def campaign_status(campaign_id: str):
    report = get_report(campaign_id)
    if report is None:
        raise HTTPException(404, "Campaign not found")
    return {"campaign_id": campaign_id, "status": "complete", "scenario": report["scenario"]}


@app.get("/api/campaigns/{campaign_id}/events")
def campaign_events(campaign_id: str):
    events = get_events(campaign_id)
    if events is None:
        raise HTTPException(404, "Campaign not found")
    return events


@app.get("/api/campaigns/{campaign_id}/report")
def campaign_report(campaign_id: str):
    report = get_report(campaign_id)
    if report is None:
        raise HTTPException(404, "Campaign not found")
    return report
