# ADR 0015: Reusable banking controls and usefulness evaluation

- **Status:** Accepted
- **Ticket:** T13

## Context

The repository already has focused tests for protected authorization, but no
reusable result that can later appear in an assessment report. T13 must also
check normal assistant behavior through the same runtime, without treating a
model refusal as proof of enforcement.

## Decision

Add a small ordinary-Python evaluator. It runs direct control probes against
the session-bound reference profile, then runs benign questions through the
selected target using the shared assistant runtime. Return separate typed
results with run IDs, evidence IDs, origin, expected facts, and observed output.
Derive expected banking facts independently from the immutable snapshot.

Use five cases currently supported by the shared runtime: latest transfer,
recent spending, grocery spending, latest transaction, and refusal of an
unrelated question. Defer trusted clickable-link evaluation until T18 creates
typed actions and an enforcing renderer.

## Alternatives considered

1. **Keep isolated unit tests only.** Simple, but the product cannot reuse their
   results in future assessments or reports.
2. **Adopt a general evaluation framework now.** Adds another abstraction before
   Sentinel needs model comparisons, repeated-trial statistics, or a provider
   matrix.
3. **Use a focused typed Python evaluator (chosen).** Reuses actual gateway,
   repository, evidence, and assistant runtime behavior; creates a reportable
   contract without a new dependency or migration.

## Consequences

- Direct controls and agent usefulness cannot be conflated in the report.
- Fixture results verify integration and deterministic facts, not broad language
  quality or live-model resistance.
- The protected profile remains a control target; selected-target chat is the
  subject of usefulness checks.
- T18 owns real trusted-link checks.
