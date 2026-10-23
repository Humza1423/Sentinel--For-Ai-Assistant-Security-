# Changelog

## T02 — Observed evidence recorder

- Added typed observed events, canonical sanitized-payload digests, causal parents,
  atomic per-run ordering, separate persistence and read-only paginated retrieval.
- Instrumented actual tool requests/validation, permission decisions and repository
  reads, including denied, no-data, failure and async execution paths.
- Added secret redaction and normal SQL append-only protections; preserved legacy
  reports and all existing banking data through additive migration 0003.
- Added a temporary-bank, tool-only evidence demo with no model calls.
- Reorganized the authoritative plan into six product phases, kept ticket IDs,
  added Investigator/Defense/Coding Agent repair tickets and explicit execution
  order, and archived the original deterministic-MVP design.
- Chat, model runtime integration, agents and generated patch execution are not
  implemented in this ticket. Provider usage remains $0.

## Initial GitHub publication

- Published the existing deterministic banking security MVP and T01 together as
  the initial repository state; earlier development history is not reconstructed.
- Added strict resolved-target contracts, actual-tool manifests, and the local
  configuration-inspection endpoint in T01.
- Added a strict bank tool wrapper after tests exposed LangChain's zero-field
  input-validation fast path. Invalid identity arguments cause no repository read.

## GitHub workflow setup

- Added ticket branches, PR and issue templates, ownership, and contribution guidance.
- Added locked backend lint/format/tests and frontend test/type-check/build jobs.
- Added isolated, migrated test databases and blocked provider HTTP transports.
- Added the current roadmap and per-ticket learning/review instructions.
- Kept credentials, local data, caches, and generated artifacts out of version control.
