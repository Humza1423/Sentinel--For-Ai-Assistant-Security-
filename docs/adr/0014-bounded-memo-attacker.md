# ADR 0014 — Attack the resolved banking assistant through one memo channel

## Decision

Project only registered tool names, descriptions, schemas, controlled arguments
and policy facts from the resolved target manifest into an attacker-facing
surface. Exclude configurable system instructions, records, protected markers
and internal traces. Validate generated JSON against one strict cross-customer
objective and one `transaction.memo` channel. Trusted code selects the owned
transfer, creates a run-specific immutable overlay and limits attempts to three.

Each candidate gets a fresh assistant run and the T10 evidence scorer. The
attack trial is `not_exposed` unless the actual tool result contains the memo's
digest and a later model dispatch references that result. Model resistance is
reported only after exposure. Fixed seeds and fake models are explicitly
labeled; their scripted decisions are never called live exploit evidence.

The live attacker uses the existing Responses adapter and `UsageBroker` with
role `attacker` and the same assessment ID as any live target calls. The first
live assessment is limited to one attempt. No provider call is part of normal
tests or CI.

## Alternatives

Passing the complete manifest would expose arbitrary system instructions and
future configuration fields. A large red-team framework would add a second
event model before one banking scenario works. Generating payloads without
executing them would not show an observed result. We chose a small provider
interface, strict candidate contract and the existing assistant runtime.

The live adapter could have been duplicated for the attacker. Reusing its
bounded transport and budgeted invoke path keeps target and attacker usage
rules aligned, with a role-specific structured output schema.

## Limits

This ticket does not create a campaign UI, replay, source investigation or
generated repair. A fixture target can show that the instrumentation works, not
that a real model was persuaded. Exposure plus a violation is an observation
from a trial; it does not by itself prove the memo caused the behavior. Live
trials remain opt-in and require a separately approved spend scope.
