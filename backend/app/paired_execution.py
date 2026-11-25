"""Two isolated assistant runs with independently observed controlled inputs."""

from collections.abc import Callable
from typing import Literal
from uuid import UUID, uuid4

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from .bank import BOB_MARKER, SnapshotBankRepository
from .evidence import EvidenceRecorder
from .live_model import MeteredOpenAIModel
from .observed_scoring import CrossCustomerVerdict, read_run_trace, score_cross_customer_run
from .runtime import AssistantRun, run_assistant
from .target_contracts import RequestContext, TargetConfig


class PairedComparison(BaseModel):
    baseline_run_id: UUID
    candidate_run_id: UUID
    status: Literal["matched", "mismatched", "inconclusive"]
    unexpected_fields: tuple[str, ...] = ()
    declared_config_changes: tuple[str, ...] = ()
    evidence_ids: tuple[UUID, ...] = ()
    reason: str = ""


class PairedResult(BaseModel):
    comparison: PairedComparison
    comparison_kind: Literal["candidate_configuration", "reference_control"]
    baseline: AssistantRun
    candidate: AssistantRun
    baseline_verdict: CrossCustomerVerdict
    candidate_verdict: CrossCustomerVerdict
    repair_verified: Literal[False] = False


def compare_executions(baseline_run_id, candidate_run_id, *, declared_changes=()):
    result = PairedComparison(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        status="inconclusive",
        declared_config_changes=tuple(sorted(declared_changes)),
    )
    if baseline_run_id == candidate_run_id:
        result.reason = "Two independent runs are required."
        return result
    receipts = []
    dispatches = []
    sources = []
    origins = []
    for run_id in (baseline_run_id, candidate_run_id):
        events, origin = read_run_trace(run_id)
        requests = [e for e in events if e.name == "request.received"]
        if (
            len(requests) != 1
            or requests[0].provenance.get("execution_receipt") != "system_trusted"
        ):
            result.reason = "An independently recorded input receipt is missing."
            return result
        receipt = requests[0].payload.get("execution_receipt")
        source = requests[0].payload.get("source_receipt")
        if (
            not isinstance(receipt, dict)
            or not isinstance(source, dict)
            or source.get("status") != "verified"
        ):
            result.reason = "Source or input identity is unavailable."
            return result
        calls = [
            e for e in events if e.name == "model.requested" and e.payload.get("call_number") == 1
        ]
        sent = [
            e
            for e in events
            if e.name == "context.dispatched"
            and len(calls) == 1
            and (e.parent_event_id == calls[0].event_id or calls[0].parent_event_id == e.event_id)
        ]
        if len(sent) != 1 or not sent[0].payload.get("message_digests"):
            result.reason = "The initial model dispatch is missing."
            return result
        dispatches.append(sent[0].payload["message_digests"])
        if any(
            e.payload.get("snapshot_digest") != receipt.get("snapshot_digest")
            for e in events
            if e.name == "repository.read_completed"
            and e.payload.get("snapshot_digest") is not None
        ):
            result.reason = "The database read used a different snapshot."
            return result
        receipts.append(receipt)
        sources.append(source["digest"])
        origins.append(origin)
        result.evidence_ids += (requests[0].event_id,)
    left, right = receipts
    required = {
        "schema_version",
        "user_digest",
        "history_digest",
        "session_id",
        "customer_id",
        "snapshot_id",
        "snapshot_digest",
        "memo_digest",
        "config",
        "tool_schema_digest",
    }
    if set(left) != required or set(right) != required:
        result.reason = "Input receipt fields are incomplete."
        return result
    differences = [
        key for key in required - {"config", "tool_schema_digest"} if left[key] != right[key]
    ]
    actual_changes = {
        key
        for key in TargetConfig.model_fields
        if left["config"].get(key) != right["config"].get(key)
    }
    if actual_changes != set(declared_changes):
        differences.append("declared_config_changes")
    if left["tool_schema_digest"] != right[
        "tool_schema_digest"
    ] and not actual_changes.intersection({"tool_profile", "policy_preset", "defense_presets"}):
        differences.append("tool_schema_digest")
    if left["config"]["model"] != right["config"]["model"]:
        differences.append("model_settings")
    start = 1 if "system_instructions" in actual_changes else 0
    if dispatches[0][start:] != dispatches[1][start:]:
        differences.append("consumed_messages")
    if sources[0] != sources[1]:
        differences.append("source")
    if origins[0] != origins[1]:
        differences.append("execution_mode")
    result.unexpected_fields = tuple(sorted(differences))
    result.status = "mismatched" if differences else "matched"
    return result


def execute_pair(
    *,
    baseline_config: TargetConfig,
    candidate_config: TargetConfig,
    context: RequestContext,
    user_message: str,
    baseline_model_factory: Callable,
    candidate_model_factory: Callable,
    declared_changes: tuple[str, ...],
    history: tuple[BaseMessage, ...] = (),
    memo_transaction_id: str | None = None,
    memo: str | None = None,
    comparison_kind: Literal[
        "candidate_configuration", "reference_control"
    ] = "candidate_configuration",
    live: bool = False,
    assessment_id: UUID | None = None,
) -> PairedResult:
    """Execute a frozen case twice. Generated source revisions arrive via later isolation work."""
    if (memo is None) != (memo_transaction_id is None):
        raise ValueError("A memo and its owned transaction are required together")
    if set(declared_changes) - TargetConfig.model_fields.keys() or "model" in declared_changes:
        raise ValueError("Only known non-model configuration changes may be declared")
    profile_changed = any(
        getattr(baseline_config, key) != getattr(candidate_config, key)
        for key in ("tool_profile", "policy_preset", "defense_presets")
    )
    if profile_changed and comparison_kind != "reference_control":
        raise ValueError("Prebuilt tool and defense profiles are reference comparisons")
    if live and assessment_id is None:
        raise ValueError("Live paired runs require an assessment budget")
    runs, contexts, models = [], [], []
    for config, factory in (
        (baseline_config, baseline_model_factory),
        (candidate_config, candidate_model_factory),
    ):
        recorder = EvidenceRecorder.start(origin="live_execution" if live else "fixture_execution")
        ctx = context.model_copy(update={"request_id": str(uuid4())})
        if memo is not None:
            repository = SnapshotBankRepository()
            repository.apply_memo_overlay(ctx, str(recorder.run_id), memo_transaction_id, memo)
            import hashlib

            recorder.append(
                "attack.overlay_applied",
                "application",
                {
                    "overlay_run_id": str(recorder.run_id),
                    "snapshot_id": repository.snapshot.snapshot_id,
                    "transaction_id": memo_transaction_id,
                    "memo_digest": hashlib.sha256(memo.encode()).hexdigest(),
                },
                provenance={"memo_digest": "external_untrusted"},
            )
        model = factory(recorder)
        if any(model is previous for previous in models):
            raise ValueError("Every paired run requires a fresh model")
        models.append(model)
        try:
            if live != isinstance(model, MeteredOpenAIModel):
                raise ValueError("Model execution mode does not match")
            if live and (model.recorder is not recorder or model.assessment_id != assessment_id):
                raise ValueError("Model must use the same assessment budget and its own run")
            run = run_assistant(
                config=config,
                context=ctx,
                user_message=user_message,
                model=model,
                history=history,
                recorder=recorder,
                memo_overlay_run_id=str(recorder.run_id) if memo is not None else None,
            )
            runs.append(run)
            contexts.append(ctx)
        finally:
            if isinstance(model, MeteredOpenAIModel):
                model.close()
    comparison = compare_executions(
        runs[0].run_id, runs[1].run_id, declared_changes=declared_changes
    )
    return PairedResult(
        comparison=comparison,
        comparison_kind=comparison_kind,
        baseline=runs[0],
        candidate=runs[1],
        baseline_verdict=score_cross_customer_run(
            runs[0].run_id, contexts[0], BOB_MARKER, target_config=baseline_config
        ),
        candidate_verdict=score_cross_customer_run(
            runs[1].run_id, contexts[1], BOB_MARKER, target_config=candidate_config
        ),
    )
