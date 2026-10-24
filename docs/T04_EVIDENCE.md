# T04 — Tools with an honest permission boundary

## What changed

T04 connects the synthetic bank to reviewed, typed LangChain tools. A small
Python gateway binds protected requests to the trusted session and records
allow/deny decisions. The safe snapshot repository independently scopes reads.
The deliberately unsafe foreign-customer lookup lives in a named lab repository,
not a bypass switch on the ordinary repository. The target manifest is built from
those executable tools, including the lab's mixed tool authority.

## Data flow

```text
Caller-proposed tool name/arguments (model-origin evidence arrives in T05)
→ LangChain tool validates the schema and records the request
→ Python gateway chooses effective customer scope and records the decision
→ protected snapshot query or explicitly vulnerable synthetic lab lookup
→ repository records actual returned record IDs/owners
→ tool returns data (memo remains external_untrusted)
```

The selected vulnerable lab target is the assistant that a future assessment
demo will show and attack. A protected profile is only a separate control test.
After “Generate Fix,” later tickets must test a Coding Agent's patch to an
isolated copy of the lab target; switching to the reference profile is not a fix.

## What the model and trusted code control

The model can choose exposed tools and their allowed arguments. In the lab
lookup, `customer_id` is deliberately model-controlled. In protected tools,
that argument does not exist; the gateway gets identity from `RequestContext`.
Trusted Python code owns validation, effective scope, repository access and
evidence. T04 does not guess whether a direct tool call came from a model or an
attacker memo. No model or LangGraph campaign executes in this ticket.

## Verification and limits

Focused tests cover forged arguments, invalid categories, foreign transaction
IDs, lab foreign reads, overlay isolation, accurate manifests, denial with zero
reads, and evidence causality. The historical scripted campaign still runs and
is not relabeled as an observed model assessment. T05 will add the shared model
loop and context-delivery events; T06–T07 will add chat. T04 does not generate or
verify a patch.

## Interview explanation

“I separated proposed agent tool calls from trusted permission decisions. The
manifest reflects actual schemas, and an evidence trail shows requested identity,
effective identity, and record ownership. The unsafe path is isolated as a
synthetic lab target so later repair tests can assess a real boundary.”
