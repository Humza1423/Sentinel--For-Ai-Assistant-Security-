from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Provenance = Literal["system_trusted", "authenticated_user", "bank_record", "external_untrusted"]
Verdict = Literal["violated", "blocked", "inconclusive", "error"]


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    description: str
    attack_seed: str
    request: str
    attacker_control: str
    protected_boundary: str


class CampaignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str
    mode: Literal["scripted", "live"] = "scripted"


class EvidenceEvent(BaseModel):
    sequence: int
    kind: str
    detail: str
    provenance: Provenance = "system_trusted"
    event_id: str = ""
    parent_event_id: str | None = None
    digest: str = ""


class ViolationEvidence(BaseModel):
    code: str
    supporting_event_ids: list[str]


class ToolEvent(BaseModel):
    tool: str
    requested_customer_id: str | None = None
    effective_customer_id: str | None = None
    authorization: Literal["allowed", "denied", "not_applicable"]
    outcome: Literal["returned_data", "denied", "no_data"]
    marker_in_result: bool = False


class RunResult(BaseModel):
    verdict: Verdict
    response: str
    actions: list[str] = Field(default_factory=list)
    tool_events: list[ToolEvent] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    violation_evidence: list[ViolationEvidence] = Field(default_factory=list)
    events: list[EvidenceEvent] = Field(default_factory=list)


class BenignResult(BaseModel):
    case: str
    passed: bool
    expected: str
    observed: str


class CampaignReport(BaseModel):
    campaign_id: str
    scenario: Scenario
    mode: str
    baseline: RunResult
    replay: RunResult
    defense_id: str
    benign_results: list[BenignResult]
    benign_passed: int
    benign_total: int
    snapshot_id: str
    replay_inputs_identical: bool
    model: str
    created_at: str
