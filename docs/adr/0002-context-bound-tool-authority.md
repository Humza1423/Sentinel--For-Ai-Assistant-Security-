# ADR 0002 — Bind bank identity outside the model

**Status:** Accepted for MVP

## Context

An instruction can persuade an agent to request a tool call. Prompt wording alone cannot establish that the caller may access a customer record.

## Options considered

1. Tell the model in a system prompt to use only the current customer's ID. This is easy to prototype but grants the model control over the authority-bearing argument.
2. Let the model request customer IDs, then authorize them at a gateway and repeat the check in the repository. This preserves evidence of attempted misuse and provides defense in depth.
3. Do not expose any customer ID argument to the defended tool; bind the authenticated identity in application context and repeat ownership enforcement in the repository. This narrows the authority surface most strongly, though it cannot itself stop other kinds of prompt manipulation.

## Decision

Use option 3 for the defended agent. Preserve an intentionally vulnerable synthetic tool only for the baseline scenario. Record the attempted lookup, authorization decision, and whether protected data crossed into model context.

## Consequences

- The defended LangChain tool schema has no customer identifier argument.
- The repository independently checks ownership.
- A prompt-only defense is not accepted as proof of authorization safety.
