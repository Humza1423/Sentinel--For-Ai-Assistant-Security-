# T09 — A working, metered banking conversation

Status: complete within the documented read-only synthetic banking scope.

Before T09, keyword fixtures chose banking tool arguments. Real model mode now
lets GPT-6 Luna interpret natural wording, typos and follow-ups, while ordinary
Python executes the same typed tools and records what actually happened.
Guided demo remains a clearly labeled, free set of example buttons.

## What changed and why

- History sizing uses model-visible content, not audit metadata. Before every
  call, drop the oldest complete turns if needed; never split tool-call/result
  pairs. Keep at most five prior turns and preserve full stored evidence.
- Merchant, absolute amount and excluded-category filters work consistently for
  lists, totals and comparisons. Integer-cent calculations stay in the repository.
- Lists return at most 20 records with matching count, offset and `has_more`.
  Compact JSON and page-level CAD currency keep the maximum page inside the
  unchanged conservative 12,000-unit input bound. Totals use all matching data.
- One invalid-argument correction is allowed within existing call limits.
  Identity smuggling, permission, storage and provider failures are not retried
  through that path. Errors remain errors, never scripted safe answers.
- Exact dataset dates (June 26–October 23, 2026), banking scope, unavailable
  operations and ambiguity guidance are part of the resolved target digest.
  A changed target requires a new conversation; old history is retained.

## Data flow and concepts

```text
server session + verified complete-turn history + user question
  → prepare bounded context
  → model proposes a tool call
  → typed validation → gateway → scoped snapshot repository
  → record actual result → model explains it
  → validate response/citations → persist answer and evidence
```

LangGraph has two nodes: `model` and `tool`. A tool request routes model → tool
→ model; a final answer, refusal or limit routes to the end. State holds messages,
call counts, retained history, current record IDs and evidence references.
Trusted session context and execution services remain outside model control.
LangChain supplies messages, typed tools and Responses serialization. Ordinary
Python owns identity, permissions, calculations, persistence and budget admission.

The model controls wording, tool selection and proposed arguments—not identity,
authorization, spending calculations or security verdicts. Scope instructions
guide behavior; they are not claimed to prevent prompt injection. The selected
`vulnerable_lookup_v1` target remains deliberately unsafe for later assessments.
A protected profile is still only a separate reference/control.

Important files/functions:

- `app/runtime.py::run_assistant`: shared loop, whole-turn trimming, correction.
- `app/live_model.py::MeteredOpenAIModel`: actual request sizing, brokered dispatch,
  usage and safe provider-error classification; no implicit retries.
- `app/chat.py::load_history/get_session`: verified history and stale-target flag.
- `app/bank.py::transaction_page/spending_total`: scoped filtering and exact cents.
- `app/assistant.py::make_bank_tool_profile`: executable schemas and bounded pages.
- `app/runtime_context.py`: common banking semantics, scope and date instructions.
- `frontend/src/ChatWorkspace.tsx`: one workspace, modes, renewal/error guidance.
- `scripts/live_agent_smoke.py`: explicit smoke, human and acceptance suites.

## Verification

Default checks made zero provider calls: **172 backend tests**, **9 frontend
tests**, Ruff lint/format, migration upgrade plus Alembic schema check, and
production frontend build passed. Focused regressions cover ten-turn rollover,
audit-heavy messages, actual Responses wire sizing with a maximum page, filters,
ownership, correction success/failure, stale sessions and mode labels.
Independent read-only review found the initial maximum-page sizing issue;
the compact representation fixed it without increasing the input guard. Final
review found no additional blocking defects.

### Live observations — October 27, 2026

One bounded acceptance/correction cycle was authorized, with a US$1 maximum.
The first acceptance suite ran **26 cases** rather than stopping at its first
failure. The original “this month → groceries → exclude groceries” sequence now
worked, as did typos, exact dates, merchant/amount filters, the maximum page,
mixed requests, greetings, basic banking terms and unrelated-topic refusals.

Do not erase these initial problems:

- The tenth connected turn timed out at the provider (30 seconds), with uncertain
  billing retained. Nine preceding turns completed; no fixture replaced the error.
- An ambiguous comparison invented a period; balance/cancellation requests made
  unnecessary lookups before explaining their limitations.

One focused prompt correction clarified these cases, without changing the lab
authorization policy. The **13-case targeted retest passed**: a fresh ten-turn
sequence, plus separate ambiguous comparison, balance and cancellation cases.
The final follow-up produced the independently expected CAD 129.80. The three
unsupported/ambiguous requests asked or declined without banking tool calls.
These are distinct trials, not a claim that the original 26 all passed.

Browser verification then submitted `shwo my latset trasnfer`: October 17,
CAD 125.00, matching the transfer rather than October 23's grocery transaction.
A weather question returned “I can only help with your synthetic banking
transactions, spending, transfers, and available bank actions,” with no tool read.

Local generated artifacts are `/tmp/sentinel-t09-acceptance.json`,
`/tmp/sentinel-t09-retest1.json` and `/tmp/sentinel-t09-complete.png`; these and
private SQLite traces are not committed. Earlier live gaps remain in
[the historical report](T09_LIVE_EVALUATION.md), including its run IDs.

At the release checkpoint the cumulative ledger recorded **US$0.008113**;
this completion pass added **US$0.004059**. It retained **US$0.016** uncertain
reservations (three earlier quota failures and this timeout), leaving
US$44.975887 available. Reservations are not confirmed charges. Budget was not
reset, and concurrent browser calls are included in the project total.

## Reproduce and limits

From `backend/`, after selecting the existing private key file and initializing
prior spend once, explicitly run:

```sh
uv run python -m scripts.live_agent_smoke --live --suite smoke --output /tmp/sentinel-smoke.json
uv run python -m scripts.live_agent_smoke --live --suite acceptance --output /tmp/sentinel-acceptance.json
```

Inspect smoke evidence before the larger suite. No credentials means guided demo
and all automated tests remain usable. Never paste keys or enable live CI.

This is bounded memory, not unlimited conversation; older details can be lost
and should be restated. There are no balances, money movement or current FX
rates. Citation validation proves IDs were available, not that all prose is
correct. Model refusals are observed behavior, not an enforced security fix.
Generated attacks, evidence-based security scoring and repair/replay remain later
tickets. We do not silently replace the vulnerable target with protected tools.

Interview explanation: “I built one tool-backed assistant runtime with injectable
models, bounded complete-turn memory, recorded operations and per-call budget
admission. I tested real language behavior against fixed bank facts, corrected
observed gaps, and kept failed trials visible. Future security agents will assess
this same runtime rather than a disconnected demo.”
