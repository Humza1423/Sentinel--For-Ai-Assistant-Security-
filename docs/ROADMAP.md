# Sentinel implementation roadmap

This is the current delivery record for the approved shared-runtime plan. The
root `IMPLEMENTATION_PLAN.md` is the original deterministic-MVP design and is
historical; its greenfield and future-tense statements do not describe current
implementation completeness.

The target is one banking assistant shared by chat, attacks, replay, direct
control tests, and benign evaluation. Build the cross-customer vertical slice
first, then reuse it for phishing. Every ticket has its own tests and review.

| Ticket | Layer and outcome | Dependencies | Status |
| --- | --- | --- | --- |
| T01 | Resolved target contracts and actual-tool manifest | None | Complete; 47 focused tests |
| T02 | Runtime evidence recorder and versioned persistence | T01 | Next |
| T03 | Scoped banking queries and isolated snapshots | T01–T02 | Planned |
| T04 | Executable tool profiles and policy gateway | T03 | Planned |
| T05 | Shared assistant subgraph with injectable fake model | T04 | Planned |
| T06 | Session and bounded multi-turn chat API | T05 | Planned |
| T07 | Banking chat beside a security inspector | T06 | Planned |
| T08 | Atomic budget reservations and durable usage ledger | T01–T02 | Planned |
| T09 | Live Responses adapter and explicit smoke check | T05, T08 | Planned |
| T10 | Cross-customer scorer driven by observed events | T02, T05 | Planned |
| T11 | Manifest-based surface analysis and bounded attacker | T01, T08–T10 | Planned |
| T12 | Isolated paired runs and executable defense | T05, T10–T11 | Planned |
| T13 | Direct control probes and actual benign-agent queries | T12 | Planned |
| T14 | Assessment lifecycle, cancellation, persisted SSE | T12–T13 | Planned |
| T15 | Visual proof workspace and versioned report | T07, T10, T13–T14 | Planned |
| T16 | Repeated trials, regression export, recruiter demo | T15 | Planned |
| T17 | Gateway-only versus session-bound comparison | T16 | Planned |
| T18 | Action provenance and enforceable exact-host URL policy | T05, T08 | Planned |
| T19 | Tailored phishing attacks and observed scoring | T11–T13, T18 | Planned |
| T20 | Phishing proof UI and both-family regression suite | T16, T19 | Planned |

## Next ticket: T02

GitHub tracking: [T02 — runtime evidence recorder](https://github.com/Humza1423/sentinel-agent-security-workbench/issues/1).

Replace hand-assembled event stories with a reusable recorder alongside legacy
campaigns. Capture events when operations happen, with unique IDs, run-local
sequence numbers, UTC times, correlation IDs, sanitized payloads, and digests.

Acceptance gates:

- Events persist in order, and IDs remain unique across runs.
- Canonical payload digests verify.
- Credentials and sensitive provider errors are redacted before persistence.
- Partial failed runs retain recorded evidence.
- An Alembic migration preserves existing campaign reports.
- Focused tests cover successful, denied, failed, and partially completed traces.
- Default tests make no provider calls.

Before T05, compare an explicit assistant graph with LangChain `create_agent`
using a fake-model tool trace and record the evidence in an ADR. Before T09,
reverify model pricing and finish the cost broker. Start live evidence with one
end-to-end trial; the normal assessment may then use up to three attempts.

## Non-negotiable proof rules

- Target definitions come from executable tools and enforced configuration.
- Trusted code controls authentication, authorization, and verdicts.
- Clean replay compares independently recorded consumed inputs, allowing only
  the registered defense's declared configuration/schema differences.
- Model resistance, direct-control success, and demonstrated repair remain
  separate conclusions. Timeouts and missing evidence cannot count as blocked.
- Approved URL configuration does not claim an active renderer before T18.
- Default CI and the recruiter demo are free; live runs are opt-in and budgeted.
- One approved ticket at a time, one documented PR, green checks, then main.
