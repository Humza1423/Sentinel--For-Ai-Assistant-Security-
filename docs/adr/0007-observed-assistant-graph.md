# ADR 0007: An explicit two-node assistant graph

## Decision

Use a small LangGraph loop: `model → tool → model`, with conditional exits after
both nodes. LangChain supplies messages, model binding and the T04 typed tools.
Trusted Python still owns target resolution, session identity, authorization,
evidence, output validation and limits.

## Alternatives tested

An isolated fake-model trace produced the same sequence with both LangChain
`create_agent` and the explicit graph: user message, model tool request, tool
result, model answer. `create_agent` is shorter, but recording the exact tool
result *at the next model dispatch* and applying our own terminal/error routing
would require middleware around its loop. The explicit graph exposes those two
boundaries directly. A plain Python loop would also work, but offers less clear
routing for the future campaign graph while not reducing this small graph much.

## Consequences

The graph carries messages, counters, pending tool calls, prepared-result links
and terminal status. `RequestContext`, executable tools and the evidence recorder
stay in trusted closures, outside model-writable state. The final response is a
validated data object, and its fixed format instruction appears in the target
manifest. Malformed output, refusal, unknown tools and limits never
become a scripted success. Failed tool calls cannot route back to the model.

This is one-turn execution, not the T06 session store or T12 paired campaign.
The existing scripted campaign stays labeled legacy. Live model wiring waits for
T08 accounting and T09 integration; the T05 tests use injected fake models only.
