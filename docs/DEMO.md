# Try Sentinel locally

Start the two local services using the [README setup](../README.md#run-locally). Keep the browser in **Guided demo**. The walkthrough uses a synthetic bank, fixture model and real local tools. It requires no API key.

1. **Use the assistant.** Choose **Show my latest transfer**. The signed-in customer’s peer transfer is CAD −125.00. Inspect the answer to see which tool read the record.
2. **Read an example incident.** Choose **Assess assistant**. Step through the diagram beside the example conversation. A foreign record reached model context even though the final reply sounded ordinary. Playback summarizes a known fixture. **Open banking chat** switches the side panel to your own session.
3. **Measure the current assistant.** Choose **Review defense checks → Run banking checks**. This starts a fresh local assessment. Under **Who chooses the customer?**, compare the selected assistant’s tool with the copy using the registered session-binding defense.
4. **Inspect the proof.** Open each capability's evidence and use **Back to assessment** to return. Expand a banking question to compare both answers. A passing run requires four distinct permission checks, five successful banking questions on each copy and five comparisons with receipts from the corresponding runs.
5. **Keep the result.** Choose **Download report**. The JSON contains the saved assessment and evidence references. The example incident and the fresh permission assessment answer different questions. A passing permission check establishes the tested control's behavior on the synthetic bank.

## Repeat the browser check

With both services listening on their default local ports, run these commands from the frontend directory:

```sh
npx playwright install --only-shell chromium
npm run test:walkthrough
```

The check opens a fresh browser session, steps through playback, asks a guided banking question, runs verification, opens the two recorded scope events and compares the downloaded JSON with the server's saved report. Each invocation creates a synthetic session and assessment in the configured local database. The browser closes at completion. The ordinary frontend unit tests run separately with `npm test`.
