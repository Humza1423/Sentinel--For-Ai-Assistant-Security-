# T13 — direct controls and benign assistant evaluation

## What changed

Added a reusable Python evaluator that runs two separate checks:

1. Four direct probes exercise the protected reference tool schema, gateway,
   repository ownership boundary, and an allowed owned-record read.
2. Five ordinary questions run through the selected target and the shared
   assistant runtime: latest transfer, recent spending, grocery spending,
   latest transaction, and an unrelated-question refusal.

Each result has its own outcome and links to the persisted evidence events that
support it. The benign result records the selected target digest, snapshot
identity, response, citations, and fixture/live origin. Expected totals and
transaction facts come independently from snapshot contents, not from the
assistant's own tool results.

## Why the two results stay separate

Direct probes establish how trusted application controls behave when given
representative requests. Agent checks show what the selected assistant actually
did for ordinary questions. A passing probe does not imply that the model is
safe, and an assistant refusal does not prove that an access control worked.

The built-in offline model remains intentionally narrow. These fixture checks
verify that the evaluation wiring reaches the real tools and runtime; they do
not claim broad natural-language understanding. Live evaluation remains opt-in
and must use the existing metered model path.

## Scope decisions

- Benign questions run against the selected target, including the vulnerable
  synthetic lab target, so evaluation describes the assistant the engineer
  configured.
- The protected profile is used only for direct control probes.
- The previous trusted-help-link example stays in the legacy scripted campaign.
  A real link action check waits for T18, which introduces typed actions and an
  enforcing renderer. Until then, target prose is not a trusted clickable action.
- No database migration, network integration, or model call was added.

## Verification

- Four direct probes pass against actual tools and repository/gateway code.
- Five deterministic assistant cases pass through `run_assistant`.
- A deliberately refusing fake model causes banking-usefulness failures while
  the direct-control results remain independently passing.
- The default backend suite remains provider-free.

The T13 learning point: an evaluation is a contract over observable behavior,
not a model-written judgment. The code computes expected facts and compares
them with the real runtime's response and evidence.
