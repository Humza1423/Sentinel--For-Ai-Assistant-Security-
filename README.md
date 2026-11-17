# Sentinel

**See what an AI agent actually did, and where trust broke.**

Sentinel is a local security workbench for tool-using AI assistants. It pairs a
synthetic banking chatbot with an inspector for tool calls, access decisions,
database reads, and model outputs, so a security finding can point to execution
evidence.

The core question is simple: if untrusted text asks an assistant to access
someone else's data, what actually happens at the tool boundary?

[Try the local demo](docs/DEMO.md) · [Run locally](#run-locally) ·
[Engineering decisions](#engineering-decisions) ·
[Threat model](docs/THREAT_MODEL.md) · [Roadmap](docs/ROADMAP.md)

[![CI](https://github.com/Humza1423/Sentinel--For-Ai-Assistant-Security-/actions/workflows/ci.yml/badge.svg)](https://github.com/Humza1423/Sentinel--For-Ai-Assistant-Security-/actions/workflows/ci.yml)

## What you can inspect today

| Area | Implemented behavior | Evidence and boundary |
| --- | --- | --- |
| Banking chat | Persisted conversations use a shared LangGraph/LangChain runtime and typed banking tools | [Live-chat evidence](docs/T09_EVIDENCE.md). Guided mode is a narrow offline fixture; real-model mode is opt-in and metered |
| Tool authorization | Trusted application code binds identity and enforces access for the protected profile | [Tool gateway](backend/app/gateway.py). The separate synthetic lab target deliberately includes an unsafe lookup |
| Runtime evidence | Record actual tool requests, decisions, reads, context, and outputs in SQLite | [Evidence walkthrough](docs/T02_EVIDENCE.md). Observed runs remain separate from scripted reports |
| Attack trials | A bounded Python backend runner derives an attack surface from real tools and inserts candidate text into an isolated transaction memo | [Attack implementation](backend/app/attack.py), [T11 evidence](docs/T11_EVIDENCE.md). This is not yet the complete attack/repair dashboard |
| Security scoring | Deterministic code traces a synthetic cross-customer marker through recorded reads, model context, and output | [Observed scorer](backend/app/observed_scoring.py), [T10 evidence](docs/T10_EVIDENCE.md) |
| Useful-task checks | Four direct control probes and five ordinary assistant questions are evaluated separately | [Evaluator](backend/app/evaluation.py), [T13 evidence](docs/T13_EVIDENCE.md). Offline results establish fixture behavior |
| Scripted campaigns | Fixed phishing and cross-customer scenarios demonstrate baseline, registered controls, replay, and benign checks | [Demo guide](docs/DEMO.md). These outcomes are controlled fixtures |

**Still planned:** evidence-linked investigation, generated remediation plans,
isolated code repair, and clean verification of a candidate patch. The
[roadmap](docs/ROADMAP.md) separates completed layers from these future steps.
A registered defense in the scripted demo is not a model-generated code fix.

## Engineering decisions

- **Identity comes from the application.** A model cannot authorize itself by
  passing a different customer identifier. Protected controls live in the
  [gateway](backend/app/gateway.py) and banking repository.
- **Exposure must be established before interpreting an attack.** The
  [attacker](backend/app/attack.py) checks whether its exact memo reached model
  context. A memo the assistant never read is not evidence of resistance.
- **Verdicts come from recorded behavior.** The
  [scorer](backend/app/observed_scoring.py) links findings to events rather than
  asking the model to grade its own answer.
- **Security and usefulness are separate checks.** An assistant that refuses
  every request may avoid disclosure while failing ordinary banking tasks.
  The [evaluator](backend/app/evaluation.py) tests both.
- **Paid calls have a durable budget boundary.** The
  [usage broker](backend/app/budget.py) reserves and records metered work;
  ordinary tests block provider HTTP calls.

**Stack:** Python · FastAPI · Pydantic · LangChain · LangGraph · SQLite · SQLAlchemy · Alembic · React · TypeScript

## Run locally

Requirements: Python 3.12+, `uv`, and Node.js 22.

```bash
cd backend
uv sync --locked --extra dev
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Run backend tests with `cd backend && uv run --locked pytest -q`;
check the UI with `cd frontend && npm run build && npm test`. Backend tests apply
Alembic migrations to a temporary database and block external provider HTTP requests.
They do not read or modify your local bank database. Full quality commands are in
[CONTRIBUTING.md](CONTRIBUTING.md).

No API key is required for the local experience. Do not commit keys or `.env*`
files. SQLite persists conversations, evidence and budget accounting. Select a
private key file using `OPENAI_ENV_FILE` before starting the backend. Initialize
accounting below, then click “Real model.” Guided demo uses example buttons, not
free-text interpretation. New conversations retain their
selected mode. Adding a key alone does not enable provider calls. Live requests
use GPT-6 Luna through the usage broker, with a US$0.024 maximum per turn.

Before live use, check previous Sentinel API spend and initialize accounting once:
`cd backend && uv run python -m app.budget --prior-spend-usd AMOUNT`.
Use zero only when no earlier project charges exist. `/api/v2/usage` reports the
accounting start, prior amount, recorded usage and uncertain reservations. The
ledger enforces US$45 project/US$2 assessment ceilings for brokered calls and cannot
track unrelated applications using the same key. See [T08 notes](docs/T08_EVIDENCE.md).

## Evidence and limits

This is a synthetic research and development environment, not a production bank.
Balances, money movement, live exchange rates, production authentication, and
external targets are unsupported.

Fixture execution, live attacker execution, and live target execution are
distinct evidence categories. A live attacker does not imply the target was a
live model. `not_exposed` means the memo did not reach the model;
`no_violation_observed` is scoped to the tested trial and defined invariants.

The default banking chat and scripted campaigns can be explored without an API
key. Real-model calls remain opt-in. Model prose is not a guarantee of accuracy
or prompt-injection resistance. Chat retains at most five complete prior turns,
subject to an input bound.

## Follow the code

| Start here | What to follow |
| --- | --- |
| [Chat workspace](frontend/src/ChatWorkspace.tsx) → [chat API](backend/app/chat_api.py) | A question becomes a persisted turn with an observed run |
| [Assistant runtime](backend/app/runtime.py) → [gateway](backend/app/gateway.py) | A proposed tool call reaches trusted application controls |
| [Evidence recorder](backend/app/evidence.py) → [observed scorer](backend/app/observed_scoring.py) | Execution events become a supported security verdict |
| [Attack runner](backend/app/attack.py) → [bank evaluator](backend/app/evaluation.py) | Bounded adversarial trials and independent useful-task checks |

[Architecture decisions](docs/adr/) · [Contribution and quality workflow](CONTRIBUTING.md)
