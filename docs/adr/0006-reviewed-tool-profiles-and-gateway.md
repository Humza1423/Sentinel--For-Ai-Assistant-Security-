# ADR 0006: Reviewed bank tools and a small authorization gateway

## Decision

Use one small Python gateway for trusted identity binding and permission evidence.
Expose a session-bound profile with narrow read tools, plus an explicitly named
vulnerable synthetic lab lookup. The ordinary repositories never accept a
`vulnerable=True` bypass. Build target manifests from the tools actually exposed.

The lab lookup remains intentionally unsafe so the *selected lab assistant* can
be assessed later. The protected profile is a separate reference/direct-control
test, not a generated fix. A future Coding Agent must patch an isolated copy of
the vulnerable target and pass focused checks before Sentinel claims repair.

## Alternatives

- Put each permission decision inside a tool closure: less initial code, but
  duplicated authority logic and inconsistent evidence as tools grow.
- Use a general policy framework: too much machinery for one synthetic bank and
  two attack families.

The gateway makes the trust boundary explicit without a policy engine. Each
repository still checks scope independently where the profile is protected.

## Consequences

The manifest now distinguishes the lab's model-controlled lookup from its
otherwise session-bound tools. T03's snapshot fixture advances to version 2 to
include a unique second-customer marker without altering existing snapshots or
legacy demo rows. No schema migration, live model call, chatbot, or generated
repair is part of T04. Direct tool invocations are not falsely labeled as
model-origin or attacker-origin; T05 will record that origin in its assistant
runtime.
