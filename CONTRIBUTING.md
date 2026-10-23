# Contributing and ticket delivery

Sentinel uses one issue and one pull request per implementation ticket. `main` is
the tested portfolio version. The roadmap is in [docs/ROADMAP.md](docs/ROADMAP.md).

## Normal cycle

1. Review the ticket's inputs, outputs, acceptance criteria, and alternatives.
2. Start from current main: `git switch main` and `git pull --ff-only`.
3. Create a branch, for example `git switch -c codex/t02-evidence-recorder`.
4. Implement only that ticket, preserving the working demo.
5. Run focused tests and the quality commands below; inspect the complete diff.
6. Update learning notes, ADRs where needed, the roadmap, and changelog.
7. Commit with the ticket in the subject, for example
   `feat(T02): persist observed runtime evidence`.
8. Push with `git push -u origin codex/t02-evidence-recorder` and open a PR to main.
9. Wait for Backend and Frontend checks on the latest commit, then inspect the PR.
10. Squash-merge the approved ticket. Delete its merged remote branch and update
    local main with a fast-forward pull.
11. Explain what changed, show evidence, and review the next ticket before starting it.

PRs should link their issue with `Closes #number`. Include actual test results and
known limitations. Passing CI does not establish security beyond the invariants
covered by those tests. Solo maintainers do not require a second person's approval,
but checks and resolved discussions are required. Do not self-approve a PR as if
another reviewer inspected it.

## Quality checks

Backend (Python 3.12), from `backend/`:

```sh
uv sync --locked --extra dev
uv run --locked ruff check app tests migrations scripts
uv run --locked ruff format --check app tests migrations scripts
uv run --locked pytest -q
```

Tests migrate a disposable database and prohibit real HTTP provider requests. They
do not use the developer's bank or require an API key. The separate live smoke
script is never invoked by CI. Keep `uv.lock` committed and use `--locked`.

Frontend (Node.js 22), from `frontend/`:

```sh
npm ci
npm test
npm run build
```

Keep `package-lock.json` committed. CI tests both components on PRs and main, using
read-only workflow permissions and actions pinned to reviewed commit SHAs. Weekly
dependency PRs still require the same checks; they are not automatically merged.
Backend dependency changes must update `pyproject.toml` and `uv.lock` together.

## Commit attribution and publication

Commits use the maintainer's GitHub-linked noreply email. Configuration is local
to this repository. Do not backdate commits or manufacture historical ticket
commits. The initial commit records the existing MVP through T01 as it actually
existed when GitHub publishing began. Future tickets get their own PRs.

Never commit `.env` files except the placeholder `.env.example`, credentials,
SQLite files, local evidence containing secrets, or dependency/build directories.
Run `git diff --cached --check` and inspect staged filenames before publishing.

## Security reports

Use GitHub's private vulnerability reporting when enabled for a potentially
sensitive finding. Public issues are appropriate for reproducible bugs involving
the synthetic fixtures, but must never contain credentials or real bank data.
