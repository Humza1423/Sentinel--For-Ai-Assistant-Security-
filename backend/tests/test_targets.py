"""Target claims must agree with executable tools, without a database or provider."""

import asyncio
import hashlib
import json
import socket

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.bank import ALICE_ID, BOB_ID, BOB_MARKER, BankRepository, Transaction
from app.main import app
from app.target_contracts import RequestContext, TargetConfig, TargetModelConfig
from app.targets import resolve_target


@pytest.fixture(autouse=True)
def no_external_services(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Target resolution must not access a database or provider")

    monkeypatch.setattr(BankRepository, "__init__", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def context():
    return RequestContext(
        session_id="trusted-session", authenticated_customer_id=ALICE_ID, request_id="request-1"
    )


class RecordingBank(BankRepository):
    def __init__(self):
        self.calls = []

    def latest_for(self, authenticated_customer_id):
        self.calls.append(("latest_for", authenticated_customer_id))
        return Transaction("T-own", authenticated_customer_id, "Books", 20, "2026-10-22", "hello")

    def _read_latest(self, customer_id):
        self.calls.append(("lab_lookup", customer_id))
        return Transaction("T-other", customer_id, "Pharmacy", 10, "2026-10-22", BOB_MARKER)


def test_manifest_uses_actual_protected_schema_and_does_not_access_services(context):
    target = resolve_target(TargetConfig(), context=context)
    manifest = target.manifest()
    tool = target.bank_profile.tools[0]
    assert manifest.tools[0].input_schema == tool.get_input_schema().model_json_schema()
    assert manifest.tools[0].name == tool.name == "get_my_latest_transaction"
    assert manifest.tools[0].description == tool.description
    assert manifest.tools[0].model_controlled_arguments == ()
    assert manifest.tools[0].input_schema["additionalProperties"] is False
    assert manifest.tools[0].trusted_context_bindings == (
        "RequestContext.authenticated_customer_id",
    )
    assert manifest.customer_access.identity_source == "trusted_session"
    assert manifest.customer_access.repository_scope_enforced
    assert manifest.assessment_status == "not_assessed"
    assert manifest.model_execution_status == "configured_not_executed"
    assert manifest.output_actions.enforcement_status == "not_implemented"


def test_protected_tool_executes_with_trusted_identity_and_rejects_smuggled_arguments(context):
    repository = RecordingBank()
    events = []
    target = resolve_target(
        TargetConfig(), context=context, repository=repository, tool_events=events
    )
    tool = target.bank_profile.tools[0]
    for arguments in ({"customer_id": BOB_ID}, {"authenticated_customer_id": BOB_ID}):
        with pytest.raises(ValidationError):
            tool.invoke(arguments)
    assert repository.calls == []
    assert events == []
    assert json.loads(tool.invoke({}))["transaction_id"] == "T-own"
    assert repository.calls == [("latest_for", ALICE_ID)]
    assert events[0]["customer_id"] == ALICE_ID


def test_empty_tool_validation_covers_run_async_and_model_tool_calls(context):
    repository = RecordingBank()
    tool = resolve_target(
        TargetConfig(), context=context, repository=repository
    ).bank_profile.tools[0]
    forged = {"customer_id": BOB_ID}
    with pytest.raises(ValidationError):
        tool.run(forged)
    with pytest.raises(ValidationError):
        asyncio.run(tool.ainvoke(forged))
    with pytest.raises(ValidationError):
        tool.invoke({"type": "tool_call", "name": tool.name, "id": "call-1", "args": forged})
    assert repository.calls == []
    assert json.loads(asyncio.run(tool.ainvoke({})))["transaction_id"] == "T-own"
    assert repository.calls == [("latest_for", ALICE_ID)]


def test_lab_manifest_and_tool_both_expose_the_vulnerable_lookup(context):
    repository = RecordingBank()
    config = TargetConfig(tool_profile="vulnerable_lookup_v1", policy_preset="vulnerable_lab_v1")
    target = resolve_target(config, context=context, repository=repository)
    manifest = target.manifest()
    tool = target.bank_profile.tools[0]
    assert manifest.tools[0].name == "lookup_customer_transaction"
    assert manifest.tools[0].input_schema == tool.get_input_schema().model_json_schema()
    assert manifest.tools[0].model_controlled_arguments == ("customer_id",)
    assert manifest.tools[0].trusted_context_bindings == ()
    assert manifest.customer_access.identity_source == "model_argument"
    assert not manifest.customer_access.repository_scope_enforced
    assert manifest.customer_access.enforcement_locations == ()
    assert BOB_MARKER in tool.invoke({"customer_id": BOB_ID})
    assert repository.calls == [("lab_lookup", BOB_ID)]


def test_registered_defense_changes_real_tools_without_changing_instructions(context):
    config = TargetConfig(
        tool_profile="vulnerable_lookup_v1",
        policy_preset="vulnerable_lab_v1",
        defense_presets=("context_bound_customer_tools_v1",),
    )
    repository = RecordingBank()
    target = resolve_target(config, context=context, repository=repository)
    manifest = target.manifest()
    assert manifest.requested_config.tool_profile == "vulnerable_lookup_v1"
    assert manifest.effective_tool_profile == "session_bound_v1"
    assert manifest.applied_defenses == ("context_bound_customer_tools_v1",)
    assert manifest.requested_config.system_instructions == config.system_instructions
    assert manifest.tools[0].model_controlled_arguments == ()
    with pytest.raises(ValidationError):
        target.bank_profile.tools[0].invoke({"customer_id": BOB_ID})
    target.bank_profile.tools[0].invoke({})
    assert repository.calls == [("latest_for", ALICE_ID)]


@pytest.mark.parametrize(
    "changes",
    [
        {"system_instructions": "Answer banking questions concisely."},
        {"model": TargetModelConfig(reasoning_effort="medium")},
        {"model": TargetModelConfig(max_output_tokens=1000)},
        {"approved_domains": ("support.bank.example",)},
        {"tool_profile": "vulnerable_lookup_v1"},
        {"policy_preset": "session_bound_customer_v1"},
        {"defense_presets": ("context_bound_customer_tools_v1",)},
    ],
)
def test_relevant_configuration_changes_alter_digest(context, changes):
    original = resolve_target(TargetConfig(), context=context).manifest()
    changed = resolve_target(TargetConfig(**changes), context=context).manifest()
    assert changed.target_digest != original.target_digest


def test_digest_is_canonical_stable_and_excludes_session_values(context):
    target = resolve_target(
        TargetConfig(approved_domains=("Help.Bank.Example.", "other.bank.example")), context=context
    )
    first = target.manifest()
    other_context = RequestContext(
        session_id="different-session", authenticated_customer_id=BOB_ID, request_id="request-2"
    )
    second = resolve_target(
        TargetConfig(approved_domains=("other.bank.example", "help.bank.example")),
        context=other_context,
    ).manifest()
    assert first.target_digest == second.target_digest
    payload = first.model_dump(mode="json", exclude={"target_digest"})
    assert (
        first.target_digest
        == hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
    )
    serialized = first.model_dump_json()
    for excluded in (context.session_id, ALICE_ID, BOB_ID, BOB_MARKER, "OPENAI_API_KEY"):
        assert excluded not in serialized
    # Mutating an exported schema must not change the executable target or future manifests.
    first.tools[0].input_schema["properties"]["customer_id"] = {"type": "string"}
    fresh = target.manifest()
    assert "customer_id" not in fresh.tools[0].input_schema["properties"]
    assert fresh.target_digest == second.target_digest


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_profile": "arbitrary_sql"},
        {"policy_preset": "trust_the_model"},
        {"defense_presets": ["invented_defense"]},
        {"authenticated_customer_id": BOB_ID},
        {"context": {"authenticated_customer_id": BOB_ID}},
        {"tools": [{"name": "run_python"}]},
        {"enforced_policies": ["universal_injection_protection"]},
        {"manifest": {"assessment_status": "passed"}},
        {"model": {"api_key": "never-accept-secrets"}},
        {"model": {"model": "unreviewed-model"}},
        {"model": {"max_output_tokens": 2001}},
        {"model": {"timeout_seconds": True}},
        {"system_instructions": "  "},
    ],
)
def test_config_rejects_unknown_capabilities_claims_identity_and_invalid_settings(payload):
    with pytest.raises(ValidationError):
        TargetConfig.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    "host",
    [
        "https://help.bank.example",
        "help.bank.example/path",
        "*.bank.example",
        "user@bank.example",
        "bank.example:443",
        "127.0.0.1",
        "[::1]",
        "help.bаnk.example",
        "bank..example",
        "-bank.example",
        "bank.example..",
        "localhost",
    ],
)
def test_invalid_configured_hosts_are_rejected(host):
    with pytest.raises(ValidationError):
        TargetConfig(approved_domains=(host,))


@pytest.mark.parametrize("defense", ["memo_minimization_v1", "trusted_action_renderer_v1"])
def test_manifest_cannot_claim_a_registered_but_unimplemented_control(context, defense):
    with pytest.raises(ValueError, match="not executable"):
        resolve_target(TargetConfig(defense_presets=(defense,)), context=context)


def test_profile_cannot_claim_an_incompatible_policy(context):
    with pytest.raises(ValueError, match="incompatible"):
        resolve_target(
            TargetConfig(
                tool_profile="vulnerable_lookup_v1", policy_preset="session_bound_customer_v1"
            ),
            context=context,
        )


def test_resolver_revalidates_python_model_copy_bypass(context):
    forged = TargetConfig().model_copy(update={"tool_profile": "run_arbitrary_code"})
    with pytest.raises(ValidationError):
        resolve_target(forged, context=context)


def test_target_inspection_api_accepts_json_lists_and_has_no_execution_side_effects():
    with TestClient(app) as client:
        response = client.post(
            "/api/v2/targets/resolve",
            json={"approved_domains": ["HELP.BANK.EXAMPLE."], "defense_presets": []},
        )
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["output_actions"]["approved_https_hosts"] == ["help.bank.example"]
    assert manifest["assessment_status"] == "not_assessed"
    assert len(manifest["target_digest"]) == 64
    assert manifest["tools"][0]["model_controlled_arguments"] == []


@pytest.mark.parametrize(
    "payload",
    [
        {"authenticated_customer_id": BOB_ID},
        {"tool_profile": "arbitrary_sql"},
        {"defense_presets": ["trusted_action_renderer_v1"]},
        {"tool_profile": "vulnerable_lookup_v1", "policy_preset": "session_bound_customer_v1"},
    ],
)
def test_target_api_rejects_forged_authority_and_unavailable_controls(payload):
    with TestClient(app) as client:
        response = client.post("/api/v2/targets/resolve", json=payload)
    assert response.status_code == 422
