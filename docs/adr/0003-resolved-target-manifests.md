# ADR 0003 — Generate target manifests from executable tool profiles

**Status:** Accepted for T01

## Decision

Resolve a strict, versioned `TargetConfig` into the existing bank tool factory and
derive the manifest from the returned LangChain tool objects. Keep authenticated
`RequestContext` separate from engineer-editable configuration. Target resolution
does not construct a model, load credentials, initialize the bank, or execute tools.

## Alternatives considered

| Approach | Security and accuracy | Complexity and runtime | Cost, demo value, extensibility |
| --- | --- | --- | --- |
| Maintain a second, hand-written manifest registry | Descriptions can diverge from executable tools and overstate controls | Easy initially; repeated schema maintenance later | Free, but weak evidence; external adapters would duplicate declarations |
| Introspect tools alone | Accurate names and argument schemas; cannot discover ownership behavior from Python closures | Small and fast; incomplete authority description | Free and inspectable, but cannot explain the protected boundary |
| Introspect tools plus reviewed factory metadata | Exact schemas plus authority facts from the same branch that builds executable behavior | Slightly more structure; no model or database work | Free, useful inspection API, and a clear boundary for future adapters |

Choose the third approach. Behavioral tests verify the authority facts using a
recording repository. This is stronger than separately written claims, but it is
not a formal proof of arbitrary Python behavior or a completed agent assessment.

## Profiles, policies, and defenses

- `session_bound_v1` binds identity in the tool closure and reads through the
  repository's customer-filtered `latest_for` method.
- `vulnerable_lookup_v1` intentionally exposes a customer argument and the lab's
  vulnerable repository lookup.
- Policy presets must match the requested base profile. An explicit
  `context_bound_customer_tools_v1` defense can transform the resolved lab tools
  into session-bound tools while preserving the requested configuration.
- The registry's memo minimization and trusted renderer entries are not executable
  in this target yet. Resolution rejects them instead of advertising enforcement.
- Approved domains are normalized configuration only. The output manifest explicitly
  states `not_implemented` for action enforcement until T18.

## Experiment and findings

The T01 tests compare manifests with actual tool schemas and invoke those tools
against a recording repository. Initial negative tests revealed that the installed
LangChain core bypasses schema validation for zero-field tools in
`BaseTool._to_args_and_kwargs`. Extra customer arguments were discarded and the
session-bound read still ran; no foreign identity was honored, but the call was
not rejected as the schema promised.

`StrictBankTool` validates input before the conversion fast path. Tests cover
`run`, `invoke`, async invocation, and model-style tool-call envelopes, requiring
zero repository calls for rejected input. This small framework compatibility hook
must remain covered when dependencies change. T04 will build the broader policy
gateway around the same tools.

## Digest and evidence limits

The digest includes normalized requested configuration, actual schemas and tool
descriptions, effective policy facts, and declared defense transformations. It
excludes session identity values, request IDs, bank rows, and credentials. Session
and snapshot identity belong in T12 execution receipts rather than target hashes.

Exported manifests are detached descriptions. Editing one does not alter the
resolved tool objects, and the resolve endpoint never accepts a manifest as input.
Assessment status remains `not_assessed`; model settings remain
`configured_not_executed`. Existing agent and campaign entry points have not been
rewired to consume target configuration in this ticket.
