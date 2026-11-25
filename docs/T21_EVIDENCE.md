# T21 · Investigating a cross-customer read

Suppose a customer asks about a transfer. The assistant retrieves someone else's record, sees it, and replies “Finished checking your transfer.” An engineer needs to know that the read happened even though the final reply looks ordinary.

Run the focused example from the backend directory:

    uv run --locked pytest -q tests/test_investigation.py

The test runs the real gateway and repository using fixture model messages. The Investigator reports the foreign read and subsequent dispatch to the assistant. A separate finding requires evidence that the protected marker reached the customer.

## Using the report

Call `POST /api/v2/runs/{run_id}/investigation` on an observed run. The default offline analyst requires no key. It follows event parents back from the database read to the assistant's proposed tool call. An intact chain supports a plain-language explanation. A missing parent leaves the cause unresolved. Each fact has event IDs. Each cited excerpt has a file, line range and recorded Git revision.

With explicit `?mode=live`, an assessment run with an existing target charge can use the configured model once. The server obtains the assessment ID from the ledger. It sends verified code excerpts and observations with event IDs. Customer text, transaction values and credentials stay out of that packet. The existing broker handles usage. Tests exercise the actual Responses serialization against a mock transport.

## What to trust

Python establishes the facts. The optional model writes a hypothesis. Citation validation verifies that the references exist and belong to this causal chain. The engineer still evaluates whether the explanation follows from them. An invalid response leaves the facts available. The chat owner's cookie is required to investigate their chat run.

LangGraph runs the assistant. The investigation is a read-only analysis after that graph finishes. LangChain supplies the messages for a single optional model call. Source verification uses the local Git object database. Historical evidence, dirty target files, missing objects, and source archives can limit attribution. The endpoint records successful proposals as separate events. The proof workspace and generated repairs are later tickets.
