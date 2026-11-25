# ADR 0021 · Preserve assessment identity through failures

A lost start response can hide a job that already exists. Retry the same request ID until the server acknowledges it. An explicit new assessment gets a fresh ID. Update the query cache immediately and offer a loading retry when polling fails.

Move configuration validation inside worker failure handling so invalid saved settings cannot occupy the active slot indefinitely. Finalization accepts active jobs only, preserving interrupted or cancelled terminal states. Reuse the existing inspector for result evidence and require the assessment owner's session to read linked runs.

Alembic accepts an explicit database destination for isolated local demos. Preserve configured test URLs when this override is absent. This avoids changing the test harness or reading credentials.
