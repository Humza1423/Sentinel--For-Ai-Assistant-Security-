# T22 · From an investigation to a proposed repair

Suppose the Investigator traces a foreign record read to a tool that let the assistant choose a customer identity. An engineer can now ask for a repair proposal for that specific investigation. The proposal describes where the change belongs, how it would prevent the observed behavior, and which ordinary customer requests could be affected.

1. Investigate the observed run using the T21 endpoint.
2. Obtain its `investigation.proposed` event ID from the run evidence.
3. Call `POST /api/v2/runs/{run_id}/investigations/{investigation_event_id}/repair-proposal`. The default runs locally. Live analysis is opt-in and uses the original assessment budget.
4. Inspect the requested changes and verification requirements. The proposal can guide a later patch. A successful proposal means an engineer has something to evaluate. Only subsequent testing can demonstrate a fix.

The optional model reasons over the recorded cause and bounded source context. Trusted application code validates the scope and decides which checks must run. Direct permission checks test the application boundary. Replaying the original case tests the reported failure. Ordinary banking queries test whether customers can still use the assistant.

The runtime, evidence store and budget broker already exist. This stage adds one analysis step and persists the proposal through the same evidence system.
