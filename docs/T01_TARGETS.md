# T01 — Understand and inspect a target

## What changed

Sentinel can now turn reviewed configuration into a concrete tool set and a
machine-readable description of that exact set. This is the foundation for the
attacker to inspect the real attack surface later.

The existing dashboard and scripted campaigns still work as before. This ticket
does not add chat, run an assessment, or connect live models to campaigns.

## Inputs, outputs, and data flow

```text
TargetConfig (engineer settings) + RequestContext (trusted application identity)
    -> resolve_target
    -> validate the base profile/policy combination
    -> apply only executable registered defenses
    -> make_bank_tool_profile (build closures, do not execute them)
    -> ResolvedTarget containing those exact tools
    -> manifest() introspects tools and computes a canonical digest
```

`target_contracts.py` defines the strict configuration, trusted context, model
settings, and manifest types. Frozen contracts reject unknown fields and prevent
ordinary mutation. Resolution revalidates even objects constructed through
Pydantic's validation-bypassing copy helpers.

`targets.py` owns `resolve_target` and `ResolvedTarget.manifest`. The manifest
separates requested configuration from the effective protected/lab tool set.

`assistant.py` owns the executable factory, lazy repository access, and strict
bank tool input validation. Its existing `make_bank_tools` function delegates to
the same factory, so existing callers keep working.

There are no new graph state, nodes, edges, or routing in T01. The current campaign
graph is unchanged. T05 will use the resolved tools in the reusable assistant graph.

## Inspect it locally

With the existing backend running, open `/docs` to try
`POST /api/v2/targets/resolve`. It previews a configuration; it does not save it.
The handler supplies a fixed synthetic preview session and does not accept
customer identity from the request body. Real chat sessions arrive in T06.

Protected request:

```json
{}
```

The response describes `get_my_latest_transaction` with no model-controlled
arguments, a trusted session binding, and repository customer filtering.

Lab request:

```json
{
  "tool_profile": "vulnerable_lookup_v1",
  "policy_preset": "vulnerable_lab_v1"
}
```

The response describes `lookup_customer_transaction` and its model-controlled
`customer_id`. No repository scoping protection is claimed.

To inspect the real defense transformation, add:

```json
{
  "tool_profile": "vulnerable_lookup_v1",
  "policy_preset": "vulnerable_lab_v1",
  "defense_presets": ["context_bound_customer_tools_v1"]
}
```

The requested profile remains visible, while the effective profile and actual
tools become session-bound. The instructions are not changed by the defense.

Model settings and domains can be configured, for example:

```json
{
  "model": {"reasoning_effort": "medium", "max_output_tokens": 1000},
  "approved_domains": ["HELP.BANK.EXAMPLE."]
}
```

Only the reviewed Luna/Responses model combination is accepted in this ticket.
Domain entries must be exact ASCII hostnames, not URLs, wildcards, or IP addresses.
Host case, one trailing dot, ordering, and duplicates are normalized for stable
digests. No clickable-action protection is claimed yet.

## What the model controls

In the protected tool, the model has no customer argument. Trusted Python code
binds the tool to `RequestContext.authenticated_customer_id` and the repository
filters the read to that customer. In the lab tool, the customer argument is
deliberately exposed. A manifest describes these differences; it does not decide
permission or claim a live model has been assessed.

## How the tests establish the result

`tests/test_targets.py` compares declared schemas with executable tools, invokes
both profiles against a recording repository, and verifies actual identity flow.
It also checks strict argument rejection, canonical hashing, defense transformations,
unimplemented-control rejection, no identity/marker leakage, and API validation.
These focused tests prohibit bank initialization and network connection creation
and run without an API key. Existing campaigns remain regression-tested separately.

## Interview explanation

“I built target introspection around executable tools rather than hand-written
security claims. The protected tool binds identity outside the model, and tests
verify that its schema, execution, and manifest agree. I also found and corrected
an empty-schema validation bypass in the framework, with a regression test proving
rejected inputs cause no repository reads.”

## Remaining work and next ticket

T02 adds a recorder that captures events when model/tool/repository operations
actually happen. T01 has no new execution evidence, model behavior, replay proof,
or UI changes. See ADR 0003 for the alternatives and evidence behind this design.
