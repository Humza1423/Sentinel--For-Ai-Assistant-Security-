# ADR 0012 — Finish chat without creating a second agent architecture

## Decision

Keep the existing two-node assistant graph. Bound history at each model call,
using the actual pinned LangChain Responses payload for live sizing and a small
model-visible projection for fake models. Keep the independent transport guard.
Drop whole older turns with their citation/evidence references, never partial tool
pairs, while retaining the complete persisted audit trail.

Use shared Python query filters for merchant, absolute cents and category
exclusion. Return bounded pages with explicit completeness metadata; aggregates
operate on the full matching fixture, not the displayed page. Allow one sanitized
argument correction within existing limits, but not permission/storage retries.

Keep guided examples and live interpretation in the same workspace with explicit
mode labels. Do not add a separate intent classifier, chatbot framework or agent.

## Alternatives and evidence

Counting full serialized LangChain objects was simple but incorrectly counted
audit metadata; a real three-turn conversation hit the local guard. Increasing
the guard would hide that defect and increase exposure. Token-estimator-only
sizing could miss actual tool schemas and Responses reasoning. Actual payload
sizing plus whole-turn trimming preserves the existing conservative bound.
The `_get_request_payload` helper is private: dependencies remain pinned and a
mocked HTTP regression checks real serialization, including encrypted reasoning
and the maximum 20-record page. Recheck this on dependency upgrades.

Letting the model filter/sum retrieved pages worked for small examples but wasted
context and risked incomplete totals. Repository filters are deterministic,
shared and independently tested. Repeated verbose schemas made maximum pages too
large; compact schemas/result JSON fixed that without losing provenance or raising
limits. Currency remains explicit once per list page.

A separate scope classifier would add calls, latency and another source of
disagreement. Common target instructions plus representative evaluations meet
this ticket's conversational scope; they are not a security boundary. One bounded
correction handles ordinary argument mistakes without retry loops.

## Consequences

Ten-turn fake/live conversations, shared filters and scope refusals are verified.
An initial live timeout and ambiguity/unsupported-operation gaps remain recorded;
one prompt correction and a 13-case targeted retest passed. No new migration or
dependency is needed. Future attacks/replay use this runtime, and the selected
vulnerable lab tool remains unchanged rather than becoming a prewritten repair.
