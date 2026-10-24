# ADR 0005: Versioned immutable synthetic bank snapshots

## Decision

Keep legacy bank rows for the deterministic demo and add a small persisted
snapshot store for the future shared assistant runtime. Store exact canonical
contents with a dataset version, fixed reference date, content digest and
content-derived ID. Store memo changes separately by run and transaction.

Protected snapshot queries receive `RequestContext`, establish owner scope first,
then filter and calculate. The vulnerable synthetic lookup remains an explicitly
named lab path. Snapshot and overlay rows reject ordinary SQLite updates/deletes.

## Alternatives considered

- Expand the existing `transactions` table. This would change old fixtures and
  hard-coded campaign results, and its seeder skips work when any row exists.
- Hash the current bank table at run time. This identifies current data but does
  not freeze the exact contents needed for later replay.
- Create a full database copy per run. It adds migration and cleanup complexity
  without benefit for this small local dataset.

The additive snapshot and overlay tables preserve old behavior and freeze what a
run consumes. External providers remain a future adapter boundary; no network
integration is part of this decision.

## Consequences

The fixture is deterministic and CAD-only. Query calculations use integer cents.
The digest detects altered content but does not make a local SQLite file resistant
to an administrator who can replace the database or remove its triggers. Snapshot
queries record snapshot and record identity through T02 evidence; model-context
delivery is a later runtime responsibility.
