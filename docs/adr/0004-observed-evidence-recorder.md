# ADR 0004 — Record observed operations explicitly in SQLite

**Status:** Accepted for T02

## Decision and alternatives

| Approach | Benefits | Costs and limitations |
| --- | --- | --- |
| LangChain callbacks as the primary recorder | Convenient model/tool hooks | Miss ordinary repository decisions; framework-coupled; insufficient for later repair operations |
| Explicit recorder calls at execution boundaries | Accurate requested/validated/authorized/read distinctions; no model cost; reusable from graph nodes and agents | Requires a small number of deliberate hooks |
| Generic event bus or distributed log | Many consumers and remote scale | Adds infrastructure and failure modes with no benefit for a single local assessment |

Choose explicit recording with a small SQLite service. There are no queues, graph
dependencies, provider clients, or model-generated event stories in the recorder.

## Persistence and causality

`observed_runs` and `observed_events` are separate from legacy scripted campaign
tables. Events commit independently of the banking operation, preserving the trace
when that operation fails. Atomic `UPDATE ... RETURNING` sequence allocation and
event insertion share a transaction; SQLite serializes writers. A unique run/sequence
constraint is a second guard. Failed appends roll back their counter allocation.

Parents must exist earlier in the same run. Parents express causality, not an
invented sequential chain: both a tool's validation and its final completion are
children of its request, while repository completion belongs to its read-start event.

The recorder is passed explicitly to tools. A short-lived ContextVar propagates
the current run/parent through existing nested repository calls and async tool
worker threads; tokens reset in finally blocks. Tests exercise parallel async
tools with different runs. No mutable global run or shared event buffer is used.

## Security and integrity

Sanitize structured data before hashing/persistence. Mask sensitive headers/keys,
configured fields/paths, known secret values and recognizable credential strings.
Never store raw exception text or tracebacks; record error type/reason instead.
Redaction is bounded and rejects non-JSON, nonfinite, excessive-depth/size payloads.
It is not a general detector for all unknown sensitive free text; callers should
emit only needed data and configure sensitive fields.

The canonical SHA-256 digest covers the sanitized payload only. UTC/IDs/sequence,
typed names, actor and provenance are validated metadata, not a cryptographic chain.
Read-time validation checks payload digests and stored envelope identities.

SQLite update/delete triggers enforce append-only behavior for normal ORM and SQL
operations. There is no public event-write/update/delete API. Database owners can
still remove triggers or replace files, so this is not tamper-proof storage.

## Failure behavior and compatibility

If recording a request fails, its tool does not run. If evidence fails after a
repository operation, the trace may end at read-start and the tool raises; no
successful completion or safe verdict is invented. Failed database reads record
read failure and tool failure. An empty successful query is recorded as no_data.

Tools remain compatible with T01 and the existing agent adapter. Without an
explicit recorder, target inspection stays side-effect-free and legacy campaigns
retain their old fixtures. T02 does not infer that returned data reached a model.
Agent/patch/replay event names are reserved contracts, not emitted future activity.

## Evidence used for the decision

Tests cover independent concurrent writers, rollback after invalid parent IDs,
real SQLite tool reads, malformed sync/async tool calls, ownership denials, failures
before/after reads, secret masking, append-only SQL, and upgrade from a populated
0002 database. The default suite blocks provider transports; T02 costs $0.
