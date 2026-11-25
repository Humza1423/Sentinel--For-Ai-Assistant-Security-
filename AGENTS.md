# Sentinel repository working instructions

## Delivery cadence

- Use phase mode by default until the first Sentinel MVP ships. Continue
  through the agreed release roadmap without waiting for routine approval
  between tickets. Use ticket mode when the user requests a single ticket.
- Phase mode never combines tickets or bypasses gates. Every ticket still gets a
  separate branch, focused implementation, tests, documentation, independent
  review, PR, CI, and merge. Begin the next ticket only after the previous ticket
  is merged and local `main` is current; never build dependent tickets in parallel.
- Explain each ticket's purpose, inputs/outputs, alternatives, and learning
  concepts before editing. In phase mode this can be a concise checkpoint when
  those decisions were already approved in the phase brief.
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
- In ticket mode, wait for user review before beginning the next ticket. In phase
  mode, report a concise checkpoint and continue unless a new material decision,
  failed gate, new permission, paid usage, contradictory evidence, or user pause
  requires review.

## Collaboration preference

- Optimize for a strong, shippable product and the user's growth as an AI
  engineer—not merely fast completion or recruiter presentation.
- Proactively surface better approaches, real tradeoffs, and capabilities the
  user may not know to request. Disagree plainly when evidence supports a better
  direction.
- Use phase mode for well-defined, tightly connected local work. Prefer ticket
  mode or a deliberate checkpoint for high-impact architecture choices, live API
  spend, security-sensitive execution, external integrations, and generated-code
  repair boundaries.

- The coordinating agent owns the shared interface and integration decision. Delegate independent work when it saves time. Give each worker a bounded task and review its result against the ticket gate.
- Run independent backend and frontend checks in parallel. For workspace changes, also exercise the integrated flow in a browser. Review the full diff and evidence at major checkpoints.
- Commit reviewable increments such as a working interaction, regression coverage, or updated operating instructions. Keep each ticket in its own PR and retain the squash-merge rule.

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
