# Sentinel implementation roadmap

This is the status tracker for the [authoritative implementation plan](../IMPLEMENTATION_PLAN.md).
The [original deterministic MVP plan](archive/DETERMINISTIC_MVP_PLAN.md) is historical.
Ticket numbers are identifiers, not strict execution order. GitHub history keeps the same IDs.

The product combines shared banking chat, attacks, evidence, investigation, a
Defense Agent's proposal, user-triggered isolated code repair, and verified replay.
Each approved ticket has its own tests, learning review, and PR to protected main.

| Ticket | Layer and outcome | Dependencies | Status |
| --- | --- | --- | --- |
| T01 | Resolved target contracts and actual-tool manifest | None | Complete; 47 focused tests |
| T02 | Runtime evidence recorder and versioned persistence | T01 | Implemented; awaiting review |
| T03 | Scoped banking queries and isolated snapshots | T01–T02 | Implemented; PR review |
| T04 | Executable tool profiles and policy gateway | T03 | Planned |
| T05 | Shared assistant subgraph with injectable fake model | T04 | Planned |
| T06 | Session and bounded multi-turn chat API | T05 | Planned |
| T07 | Banking chat beside a security inspector | T06 | Planned |
| T08 | Atomic budget reservations and durable usage ledger | T01–T02 | Planned |
| T09 | Live Responses adapter and explicit smoke check | T05, T08 | Planned |
| T10 | Cross-customer scorer driven by observed events | T02, T05 | Planned |
| T11 | Manifest-based surface analysis and bounded attacker | T01, T08–T10 | Planned |
| T12 | Clean paired execution against a candidate revision | T11, T13, T22 | Planned |
| T13 | Direct control probes and actual benign-agent queries | T03, T05, T10 | Planned |
| T14 | Assessment lifecycle, cancellation, persisted SSE | T12–T13 | Planned |
| T15 | Investigation, diff and evidence proof workspace | T07, T14, T21–T22, T25 | Planned |
| T16 | Repeated trials, regression export, guided demo | T15, T26 | Planned |
| T17 | Gateway-only versus session-bound comparison | T16 | Planned |
| T18 | Action provenance and enforceable exact-host URL policy | T05, T08 | Planned |
| T19 | Tailored phishing attacks and observed scoring | T11–T13, T18 | Planned |
| T20 | Phishing proof UI and both-family regression suite | T16, T19 | Planned |
| T21 | Investigator Agent and evidence-linked root cause | T03, T10–T11 | Planned |
| T22 | Defense Agent and structured RemediationPlan | T08, T21 | Planned |
| T23 | Isolated Git workspace and restricted execution | T14, T22, supported sandbox | Planned |
| T24 | Coding Agent and validated patch application | T08, T23 | Planned |
| T25 | Candidate security, benign and replay verification | T12–T13, T24 | Planned |
| T26 | Accept/reject/export and explicit PR actions | T15, T25 | Planned |

## Product phases

1. **Trustworthy foundation:** T01–T04.
2. **Working banking chatbot:** T05–T09.
3. **Attack and detection:** T10–T11.
4. **Investigation and autonomous repair:** T21–T26.
5. **Verification and polished product:** T12–T16.
6. **Phishing expansion:** T17–T20.

Phases group capabilities, not chronological work. Repair and verification interleave.

## Recommended execution order

```text
T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11
→ T13 → T21 → T22 → T12 → T14 → T23 → T24 → T25 → T15 → T26 → T16
→ T17 → T18 → T19 → T20
```

## T02 evidence and review

GitHub tracking: [T02 — runtime evidence recorder](https://github.com/Humza1423/sentinel-agent-security-workbench/issues/1).

T02 adds observed tables alongside legacy stories, actual tool/repository hooks,
and a read-only paginated API. See [the T02 learning note](T02_EVIDENCE.md) and
[ADR 0004](adr/0004-observed-evidence-recorder.md). It implements no agents, chat,
patch execution, or generated repair UI. The next ticket after review is T03.

Acceptance gates:

- Events persist in order, and IDs remain unique across runs.
- Canonical payload digests verify.
- Credentials and sensitive provider errors are redacted before persistence.
- Partial failed runs retain recorded evidence.
- An Alembic migration preserves existing campaign reports.
- Focused tests cover successful, denied, failed, and partially completed traces.
- Default tests make no provider calls.

## T03 — scoped synthetic banking snapshots

T03 adds a fixed-date, 120-record CAD snapshot with exact contents and a canonical
digest, trusted-session queries, integer-cent calculations and per-run untrusted
memo overlays. Legacy demo rows and reports remain unchanged. See
[the T03 learning note](T03_EVIDENCE.md) and [ADR 0005](adr/0005-versioned-bank-snapshots.md).

Acceptance gates:

- Snapshot ID/version/reference date/digest and all transaction contents persist.
- Query scope comes from `RequestContext`; date/category/amount filters cannot
  broaden access to another customer.
- Independent totals and inclusive date-boundary tests pass using integer cents.
- Overlays retain `external_untrusted` provenance and cannot change the base
  snapshot or another run.
- The additive migration preserves existing reports, events and bank rows.
- Snapshot contents and overlays reject ordinary database update/delete.
- Backend/frontend checks make zero provider calls.

T04 is next after T03 review.

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
