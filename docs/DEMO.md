# Explore Sentinel locally

Start the backend and frontend using the [README](../README.md#run-locally).
These paths use synthetic banking data. No API key is needed for guided mode,
the scripted campaigns, or the offline evidence command.

## Banking chat and observed evidence

1. Open the app and select **Guided demo**.
2. Use one of the provided example questions. This mode is a narrow offline
   fixture, not general natural-language understanding.
3. Inspect the recorded tool call, permission decision, database read, and
   assistant response beside the conversation.
4. Follow the run's event IDs to distinguish requested actions from operations
   that actually executed.

**Real model** is a separate, opt-in mode with metered provider calls. Configure
it only after reading the [budget setup](../README.md#run-locally).

## Scripted security demo

1. Select **Scripted security demo**, then **Transaction memo phishing**.
2. Click **Run attack → repair → replay**.
3. Inspect the hostile typed action and its supporting event ID in the baseline.
4. Compare the registered rendering/minimization controls and replay result.
5. Run **Cross-customer data disclosure** and inspect the synthetic marker,
   denied lookup, five benign checks, and exportable report.

These are fixed deterministic fixtures. The button's “repair” stage applies
registered controls; it does not demonstrate an autonomous code repair or a
successful attack on a live model.

## Inspect a disposable observed tool run

From `backend/`:

```sh
uv run --locked python -m scripts.evidence_demo
```

This records a synthetic tool read and strict denial in a disposable database,
with no provider call. See the [evidence walkthrough](T02_EVIDENCE.md).

## Follow the newer attack and evaluation layers

The [bounded attacker](../backend/app/attack.py) and
[independent banking evaluator](../backend/app/evaluation.py) are implemented
Python backend components. They are not yet the complete attack/investigation/
generated-repair workflow in the dashboard.

Read [T11 evidence](T11_EVIDENCE.md) for memo exposure, attempt bounds, and
fixture/live labels, then [T13 evidence](T13_EVIDENCE.md) for the separation
between direct access-control probes and useful assistant behavior.
