# T03 — A repeatable synthetic bank

## What changed

Sentinel now persists a versioned bank snapshot with an ID, fixed reference date,
exact transaction contents and canonical SHA-256 digest. Its 120 records use
integer cents, validated dates/categories and CAD. A run can add an
`external_untrusted` memo overlay for one of its own transactions; the base
snapshot and other runs remain unchanged.

The protected `SnapshotBankRepository` takes a trusted `RequestContext`, scopes
records to its authenticated customer, then applies date/category/amount filters.
It can return transactions and calculate totals. The old `BankRepository` and its
three demo transactions remain in place for existing campaign behavior. The
vulnerable lookup is labeled as a synthetic lab repository; T04 will wire tool
profiles to explicit repository paths.

## Data flow

```text
fixed fixture + reference date
→ validate and canonicalize records
→ persist snapshot ID/version/date/digest/content
→ query using trusted RequestContext
→ apply customer ownership before filters
→ record snapshot ID/digest and returned record IDs/owners
→ optionally apply that run's untrusted memo overlay
```

## Learning points

- Integer cents avoid floating-point money errors.
- A snapshot is stored input, not just a hash of whatever happens to be in the
  live table. The digest detects changed contents when loading it.
- `RequestContext` carries trusted identity. Query filters cannot change it.
- An overlay is a separate row keyed by run and transaction. It changes what that
  run reads, not the immutable shared transaction.
- Evidence records repository results and snapshot identity; it does not claim
  that a model saw those results. Model-context recording comes with T05.
- All of this is ordinary Python, Pydantic, SQLAlchemy, SQLite and Alembic. No
  LangChain, LangGraph or external API is involved in T03.

## Verification

Run the backend suite with `uv run --locked pytest -q` from `backend/`. Focused
snapshot tests independently calculate cents totals, check inclusive date ranges,
scope by customer, recreate snapshots, isolate overlays and verify database
immutability. Migration tests check upgrade behavior while retaining old rows.

## Interview explanation

“I added deterministic, immutable synthetic bank snapshots so security tests can
replay against known data. Queries take identity from trusted request context,
and attack memos live in isolated per-run overlays with untrusted provenance.”

## Limits

The vulnerable lookup remains synthetic and isolated for reproducing the test
case. Snapshot queries are not yet exposed as model tools; T04 does that. The
dataset is CAD-only and fixed to a documented reference date. No external data
adapter or network access is implemented.
