# Sentinel repository working instructions

## Delivery cadence

- Implement exactly one approved roadmap ticket at a time. Explain its purpose,
  inputs/outputs, alternatives, and learning concepts before editing.
- Start from an up-to-date `main` and use `codex/tXX-short-description`.
- Keep the app working, preserve unrelated changes, and do not rebuild completed layers.
- Add focused tests, an ADR for important tradeoffs, learning notes, a changelog entry,
  and a status update in `docs/ROADMAP.md` for each completed ticket.
- Commit coherent changes using `feat(T02): ...`, `fix(T02): ...`, `test: ...`, or
  `docs: ...`. Push the ticket branch and open a PR targeting `main`.
- The user has authorized publishing ticket changes and merging passing PRs to
  `main`. Wait for both Backend and Frontend CI checks on the current head, inspect
  the diff, and squash-merge only the approved ticket. Never bypass failed checks,
  force-push main, or invent another person's review approval.
- Attach every created PR to this Codex chat. After merge, fast-forward local main,
  report the commit/PR/checks, explain the implementation, and propose the next ticket.
- Wait for user review before beginning that next ticket. Approval to publish the
  current ticket does not remove the learning/review gate between tickets.

## Evidence and API budget

- Keep legacy scripted results visibly separate from observed runtime evidence.
- Models may propose actions; trusted code owns identity, authorization, and verdicts.
- Default tests and CI must make zero provider calls. Use injectable fake models.
- Live calls remain opt-in. Do not wire new live paths around the planned usage broker.
- Respect the approved $45 USD development ceiling and $2 assessment ceiling.
- Never print or commit credentials, local databases, private traces, caches, or build output.

## Local quality checks

Backend, from `backend/`:

```sh
uv sync --locked --extra dev
uv run --locked ruff check app tests migrations scripts
uv run --locked ruff format --check app tests migrations scripts
uv run --locked pytest -q
```

Frontend, from `frontend/`:

```sh
npm ci
npm test
npm run build
```

The backend test harness applies actual Alembic migrations to a temporary database
and blocks HTTP provider transports. Do not weaken those protections to make a test pass.
