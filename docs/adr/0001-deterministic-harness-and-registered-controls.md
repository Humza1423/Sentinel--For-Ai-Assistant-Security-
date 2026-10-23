# ADR 0001 — Deterministic security oracle, optional model agent

**Status:** Accepted for MVP

## Context

Security demonstrations need reproducible verdicts, but live model behavior varies with model versions, provider settings, and sampling. A model should not grade itself. At the same time, an AI-engineering portfolio should show an actual model/tool agent rather than only a static prompt simulation.

## Options considered

1. Make all attack and defense outcomes live-model-driven. This is realistic but nondeterministic, costs money on every test, and can confuse a resistant model with a broken security scorer.
2. Make every target a fixed mock. This is cheap and repeatable but does not demonstrate actual LangChain tool-agent construction.
3. Keep deterministic campaign fixtures as the release oracle and provide a separate opt-in LangChain agent adapter. This keeps CI stable and makes the distinction visible, but live campaign comparison is a follow-up layer.

## Decision

Choose option 3. Scripted campaigns are labeled and locally repeatable. A separate opt-in agent adapter constructs weak and context-bound tool sets, but the UI never claims the scripted response came from an LLM. Registered deterministic controls and code-based scoring remain the source of verdicts.

## Consequences

- Default development and tests need no API key and incur no provider cost.
- An explicit live-agent smoke command is available; it can incur API usage charges.
- A future live campaign must persist model/prompt/tool versions and distinguish `violated`, `blocked`, `inconclusive`, and `error`.
- Adding live runs must not replace deterministic regression fixtures.
