# T02 — Evidence you can trust

## The simple idea

An event is an observation recorded by application code when an operation happens.
It is not a story composed afterward by the campaign or an AI model.

T01 tells us what a target can do. T02 tells us what its executable tools actually
did. Later investigators can propose a cause, but their proposals must refer to
these observations. The [implementation plan](../IMPLEMENTATION_PLAN.md) explains
the six product phases and the non-numerical execution order.

## Try the real tool-only demonstration

From `backend/`:

```sh
uv run --locked python -m scripts.evidence_demo
```

This applies the real migrations to a temporary database, invokes an actual
session-bound banking tool, and then attempts a forged customer-ID argument in a
separate run. It prints sanitized evidence and disposes only that temporary
database. There is no model, live API call, UI change, or claim of agent intelligence.

For application-created runs, inspect the persisted records using:

```text
GET /api/v2/runs/{run_id}/events?after_sequence=0&limit=200
```

The response contains origin, run/attempt identity, events, a pagination cursor,
and has_more. Unknown runs return 404. Invalid pagination returns 422. Unavailable
or invalid stored evidence returns 503. There is no public event insertion route.
The temporary demo's runs are intentionally not retained for this API.

## What we built and where it fits

```text
EvidenceRecorder.start
  → resolve_target(..., evidence=recorder)
  → actual StrictBankTool invocation
       → request event
       → strict argument validation
       → tool permission decision and effective identity
       → repository ownership/scoping decision
       → real SQLite read starts and completes
       → tool completes
  → ordered, sanitized events in separate observed tables
```

`app/evidence.py` owns strict versioned event contracts, redaction, canonical
payload hashing, atomic sequence allocation, call-local causality and retrieval.
Its core interface is start, append and read; it does not depend on LangChain or
LangGraph. Future graph nodes can call append directly.

`app/assistant.py` wraps sync and async tool execution, including T01's strict
zero-argument validation. `app/bank.py` records repository permission and actual
reads. It stores record IDs/ownership and memo provenance, not entire memo text or
the protected marker.

`app/store.py` and migration 0003 add observed_runs/observed_events without replacing
legacy campaign tables. `app/main.py` exposes read-only pagination.

No graph state, nodes, edges or routing changed in T02. Existing scripted campaign
reports remain scripted. Chat, runtime model events, attacks, investigators and
repairs belong to later tickets.

## Inputs and outputs

The recorder accepts a typed event name, actor, JSON payload, field provenance and
optional parent event ID. It allocates run-local sequence, UUID event ID and UTC
time, sanitizes before storing, and returns a persisted event with a payload digest.
Run/attempt identity and execution origin remain associated across retrieval.

Parents show which operation caused another. A repository read completes under
its read-start event. Concurrent calls may interleave in sequence but keep their
own request parents and run identities.

## What trusted code controls

The recorder owns IDs, sequence allocation, redaction and persistence. The tool
closure owns authenticated identity. Repository code owns scoped access and records
whether a query actually ran. The model does not authorize or score anything here;
no model is invoked by this ticket.

A denied malformed call yields only tool.requested → tool.denied. A direct foreign
repository request records its actual denial and never emits read_started.
Returning a tool result does not prove context delivery, so no context/model event
is emitted. A missing row is no_data, not a successful protected-data read.

## How tests establish the behavior

- Canonical hashes, UUIDs, UTC, strict fields, provenance and parent validation.
- Atomic sequences with separate recorder instances writing concurrently.
- Redaction before database persistence, including custom fields and key values.
- Normal SQL update/delete rejection and payload integrity checks on retrieval.
- Actual protected/lab tool reads and strict malformed sync/async invocations.
- Repository denial, no-data, query failure and persistence failure paths.
- Separate async tool contexts without mixed run/parent identities.
- Migration of a populated 0002 database without changing its old records.
- Existing T01/legacy regressions and default no-provider-call checks.

The default test harness always migrates a temporary store and blocks provider
HTTP transports. The recorder's optional injection keeps T01 inspection free of
bank access and preserves old callers.

T02 validation: 109 backend tests passed, including all earlier regressions; Ruff
lint/format passed; the frontend test and TypeScript/Vite build passed. The actual
tool-only demo produced eight success-path events and two malformed-call events.
No provider requests were made. Local migration preserved 25 campaign reports and
three bank transactions; a backup was taken before applying the additive revision.

## Design alternatives and limits

Explicit boundary hooks were chosen over callback-only logging because database
decisions occur outside the agent framework. A generic event platform would add
no useful capability here. See [ADR 0004](adr/0004-observed-evidence-recorder.md).

Events commit independently so partial failures remain visible. If recording fails
before an operation, stop. If it fails afterward, keep the partial trace and raise;
never manufacture a success. An administrator can alter the database despite
normal append-only protections. Digests are consistency checks, not proof of
absolute integrity. Unknown sensitive text still needs appropriate configured
redaction and careful payload selection.

## Interview explanation

“I separated observed evidence from scripted fixtures. Tool validation, permission
decisions and actual database reads record themselves into an ordered, sanitized
ledger. I tested failures before and after reads, concurrent writers, and async
causality so missing evidence cannot turn into a false security success.”

## Next ticket

After T02 review, T03 adds useful banking queries, integer-cent fixtures and isolated
snapshots. It must not begin automatically during the T02 delivery.
