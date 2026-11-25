# T12 · Comparing recorded chat inputs

Two identical questions can produce different answers. For example, “show my spending” after a discussion of groceries can reach the model with different history than the same question in a fresh chat.

Use GET `/api/v2/runs/{run_id}/input-comparison/{other_run_id}` with the chat owner's cookie. Select two independent chat turns. Each side supplies its own recorded evidence. Ordered message digests represent the actual first model input after history trimming. A prepared live request alone provides insufficient evidence of dispatch.

A difference explains why two runs may be unsuitable for a controlled comparison. Matching fields establish only that those recorded inputs match. Outputs, provider internals and the effectiveness of any repair require separate evidence.

## Executing the same case twice

The Python `execute_pair` service now invokes the shared assistant twice with new run IDs, new model instances, fresh request IDs and independently created memo overlays. An initial history is copied for each invocation. A receipt is computed inside the assistant runtime from the inputs that invocation receives. The comparison checks request, history, authenticated identity, snapshot, memo contents, model settings, source and actual first dispatch. It reports every undeclared configuration change.

A tool-profile or registered-defense change must be labeled `reference_control`. It is a comparison against a prebuilt boundary. A candidate configuration uses its own label. Neither result asserts that a generated source patch was verified. Later isolated revision execution supplies that proof.

Focused tests use actual tool calls against migrated SQLite. They demonstrate a foreign read before a reference-control run, independent overlays, changed request/history detection, undeclared configuration rejection and explicit failed-run outcomes. These runs use fixture models and cost nothing. Provider-backed pairs require the existing broker, one shared assessment budget and separate per-run model adapters.

The service is ready for T14 lifecycle integration. Its result contains both conversations, observed verdicts and comparison evidence. Source-patch execution remains dependent on the later isolated-workspace ticket.
