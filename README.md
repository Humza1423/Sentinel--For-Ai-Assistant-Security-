# Sentinel — Banking Agent Security Workbench

[![CI](https://github.com/Humza1423/sentinel-agent-security-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/Humza1423/sentinel-agent-security-workbench/actions/workflows/ci.yml)

A local security lab that makes an agent vulnerability observable: replay an indirect prompt injection against a synthetic banking assistant, inspect the tool/evidence path, apply a registered control, replay the same case, and check that ordinary tasks still work.

> **Scope:** Synthetic data and deterministic fixtures only. Scripted mode demonstrates that the harness, scorer, and controls work; it does not claim that an LLM was successfully attacked or that prompt injection can be universally prevented. An opt-in LangChain model-backed agent adapter is included, but live campaigns are not connected to the dashboard yet.

**Current delivery:** T01 target inspection and T02 observed evidence are implemented.
Chat, generated attacks, investigation and code repair remain later tickets in the
[six-phase implementation plan](IMPLEMENTATION_PLAN.md).
See the [roadmap](docs/ROADMAP.md), [contribution workflow](CONTRIBUTING.md), and
[changelog](CHANGELOG.md). Ticket branches land on `main` through pull requests
after backend and frontend CI passes.

## What it demonstrates

- **Transaction memo phishing:** attacker-controlled memo text attempts to make a bank assistant recommend an external verification URL. The scorer evaluates typed actions, not inert quoted text.
- **Cross-customer disclosure:** an intentionally vulnerable lookup path returns a second synthetic customer's unique marker. The defended replay records a denied lookup and proves the marker never entered context or output.
- **Repair without blanket refusal:** five benign regression cases run after each defense.
- **Framework shape:** LangGraph owns the explicit baseline → defended replay → usefulness-check workflow; FastAPI exposes it; React presents the evidence and downloadable JSON report. The synthetic bank and campaign/evidence records live in SQLite, with Alembic schema migrations.
- **Agent engineering:** the LangChain adapter builds separate weak and context-bound tool sets. The defended tool does not accept a customer ID from the model; `OPENAI_API_KEY` is required before the provider-backed agent can be constructed.

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

No API key is required for the deterministic local experience. Do not commit API keys or `.env*` files. Campaign summaries and ordered evidence are persisted in local SQLite. To load a key from a private file without copying it into this repository, set `OPENAI_ENV_FILE` to that file's path when starting the backend; it must have mode `0600`. For example, prefix the backend command with `OPENAI_ENV_FILE="/path/to/private/key-file.env"`. The optional live-agent smoke test is `cd backend && uv run python scripts/live_agent_smoke.py` with `OPENAI_MODEL` optionally set. It makes a provider request and may incur API charges. The dashboard remains scripted-only; deterministic fixture campaigns never silently call an external model.

## Evidence and limits

The weak side is a controlled scripted fixture, not a model-generated response. The replay uses the same synthetic bank snapshot, customer identity, scenario, and request; the registered defense is the intended changed variable. Live campaign nondeterminism, provider usage traces, and real authentication remain future work. Never connect this workbench to real customer data or production tools.

## Architecture

```text
React dashboard → FastAPI → LangGraph campaign
                            ├─ scripted vulnerable target
                            ├─ policy-bound replay
                            ├─ deterministic evidence scorer
                            └─ benign regression suite
```

Initial defense registry entries are represented by stable identifiers in the campaign output: `memo_minimization_v1`, `trusted_action_renderer_v1`, and `context_bound_customer_tools_v1`. See [the threat model](docs/THREAT_MODEL.md), [architecture decisions](docs/adr/), and the [demo script](docs/DEMO.md).

## Target inspection (T01)

`POST /api/v2/targets/resolve` accepts reviewed target configuration and generates
a manifest from the actual LangChain bank tools. An empty JSON object previews
the session-bound profile. The endpoint does not save targets, access the bank,
or call a model. It rejects forged identity fields and unimplemented controls;
URL action enforcement is explicitly labeled as not implemented. Existing
campaigns and the separate live adapter have not been rewired in this ticket.

Read the [T01 walkthrough](docs/T01_TARGETS.md) for request examples, code flow,
tests, and learning notes, and [ADR 0003](docs/adr/0003-resolved-target-manifests.md)
for the alternatives and the empty-tool-schema validation finding.

## Observed evidence (T02)

Tools can now opt into a durable recorder that captures actual requests, strict
validation, permission decisions and SQLite reads. These events are separate from
the dashboard's legacy scripted reports. Inspect persisted runs with
`GET /api/v2/runs/{run_id}/events`; no client event-write endpoint exists.

Run `cd backend && uv run --locked python -m scripts.evidence_demo` for an actual
synthetic tool read and a strict denial in a disposable database, with no model or
API usage. See the [T02 walkthrough](docs/T02_EVIDENCE.md) for the data flow, tests,
failure handling and interview explanation.
