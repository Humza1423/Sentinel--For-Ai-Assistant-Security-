# ADR 0010 — Atomic local USD admission

Use one SQLAlchemy/SQLite broker and integer micro-USD, rather than an in-memory
counter or distributed billing service. SQLite BEGIN IMMEDIATE makes the project
and assessment checks atomic. Reserve before dispatch; settle confirmed usage;
retain uncertain liability after exceptions or process death. An attempt ID cannot
dispatch twice. A retry requires a fresh ID and its own admission. There is no
time-based automatic release. Read summaries use a single consistent snapshot.

Prior spend is initialized once explicitly; an unknown balance blocks dispatch.
Accounting covers this application's broker, not unrelated uses of the API key.
Provider input/output violations record actual cost and halt later admissions.

Pricing verified on 2026-10-24 from the official [model page](https://developers.openai.com/api/docs/models/gpt-6-luna)
and [pricing page](https://developers.openai.com/api/docs/pricing). Standard short
context USD/million tokens: input .10, cached input .01, 30m writes .125, 12h writes
.25, output .50. Input totals include cache partitions; reasoning is included in
output and is never counted twice. Reservations assume the highest supported
input rate. Round the complete charge upward to a micro-dollar. Price cards expire
after 30 days; reverify before changing the dated version.

T09 contract: every provider invocation passes through execute(plan, operation).
The trusted adapter receives and enforces maximum input/output tokens, uses
standard short-context processing with no regional uplift, disables hidden SDK
retries, and returns actual Usage and request ID. Missing usage retains the full
reservation. NotDispatched is allowed only when the adapter confirms no request
left the process. Confirmed usage may reconcile uncertain charges through settle;
this is a trusted service operation, not an exposed browser mutation endpoint.
Assessment preflight/batch planning will use the campaign's actual call bounds.
The former unmetered smoke adapter is disabled until T09 integrates this contract.
