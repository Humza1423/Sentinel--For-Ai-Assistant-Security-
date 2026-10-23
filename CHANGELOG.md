# Changelog

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
