# T05 — one reusable banking-assistant run

## In simple terms

Sentinel can now give a banking question to an injected fake model, let that
model request the same T04 bank tools, run the tools for real, and return a
validated answer. The model does not get to choose the customer's identity or
decide whether a tool call is allowed.

## Data flow

```text
trusted target + session + user question
→ LangGraph model node (LangChain messages/model)
→ proposed tool call
→ LangGraph tool node → T04 gateway → snapshot repository
→ tool result prepared, then dispatched to the next model call
→ validated final response or honest refusal/inconclusive/error
```

The model node records each request and proposed call. The tool node records
the executed call and links its real repository-read event to a prepared result.
`context.dispatched` is written only when that result is included in the next
model invocation. This distinction is essential: a read alone does not prove
that the model saw the data. The final output records its text and citations;
citations not backed by returned record IDs are rejected. The fixed final-JSON
instruction is included in the generated target manifest, so it is not a hidden
behavior difference.

## Authority and state

Graph state holds messages, pending calls, counters, result links and status.
Trusted `RequestContext`, target configuration, tools and recorder stay outside
model-writable state. The model may propose exposed tools and final words;
ordinary Python enforces schemas, customer scope, call limits and output shape.
The successful turn's message/tool pairs are available in memory for T06, but
are excluded from the public run summary. T05 rejects tool-bearing history on
input: T06 must validate and link its provenance before replaying prior tool
results into a new model call.

## Tests and limits

Fake-model tests run real snapshot tools, multiple calls, an untrusted memo
overlay, a foreign lab lookup, context-delivery evidence, forged and unknown
calls, malformed final output, refusal, unsupported citations, provider errors
and limits. They make no API calls. T06 will add bounded server-managed history;
T07 will put it in the UI; T08–T09 add metered live execution. The current
campaign and dashboard remain visibly scripted until later tickets replace them.
The entry point rejects non-fixture models until T08–T09 provide budgeted live
execution; it cannot silently label a paid call as fixture evidence.

## Interview explanation

“I built a small LangGraph model/tool loop around LangChain messages and typed
bank tools. The interesting part is the evidence boundary: a repository read,
prepared tool result and actual model-context dispatch are separate events.
Trusted Python, not the model, owns identity and permissions.”
