# T09 live chat evaluation — reviewed October 25, 2026

Billing is working. GPT-6 Luna answered through the shared runtime, actual bank
tools, gateway and evidence recorder. No application fixes were made after these
trials: this is the gap report requested before the next changes.

## Results

Seventeen human-style scenarios were exercised. Sixteen reached an answer or an
appropriate refusal; one ended inconclusive at the local context limit. Ten
amount/citation checks matched their expected facts, one failed to produce an
answer, and six qualitative cases were manually inspected. These are observed
usefulness results, not a security or universal-accuracy claim.

| Question/task | Observed result |
| --- | --- |
| Latest transfer | October 17, CAD 125; S-0007 |
| `shwo latest trasnfer` | Same correct transfer; category retained |
| Newest transaction | October 23, Maple Market, CAD 42.50; S-0001 |
| This month's spending | CAD 240.30; October 1–23 |
| Follow-up: Only groceries? | CAD 110.50; same month |
| Follow-up: Exclude groceries instead | **Inconclusive: context_limit** |
| October versus September | CAD 240.30 versus 344.40; decrease 104.10 |
| October 22–23 inclusive | CAD 61.45 |
| All available spending | Correct CAD 1,201.50; start-date label one day early |
| November transactions | No matching transactions; no invented records |
| Cancel transfer | Explains that chat cannot cancel transfers |
| Compare with last period, no earlier context | Asks for date ranges |
| Convert October spending to USD | Gives CAD amount; asks for an exchange rate |
| October spending excluding groceries, fresh conversation | CAD 129.80; two actual tools |
| Maple Market in October | CAD 85.00; S-0001 and S-0017 |
| Grocery purchases over CAD 40 in October | Two CAD 42.50 purchases, October 7/23 |
| February 30 | Recognizes invalid date and asks for correction; no tool call |

An initial connectivity smoke and a separate browser test of the original typo
also succeeded. The browser was explicitly switched to live mode and displayed
the tool-backed answer beside its observed events.

The main suite stopped at the failed sixth question. The remaining seven cases
were run independently, followed by four focused edge cases. The failure was
retained rather than hidden by restarting its conversation.

## Prioritized gaps and next changes

1. **Conversation memory is too restrictive.** In the sequence “this month” →
   “only groceries” → “exclude groceries instead”, the third turn executed a
   spending tool but could not make its next model call. The sizing check counts
   serialized LangChain messages, including audit metadata that is not all sent
   to the model. Stored successful turns were approximately 4.9 KB each. The
   failed turn's dispatched call reported just 866 input tokens, while the later
   local byte guard stopped execution. Do not interpret this as OpenAI running
   out of context or failing to understand the request.
   Proposed change: size model-visible conversation content, preserve full audit
   records separately, and leave room for the current tool result. Keep the
   actual wire/budget limits. Verify the exact failed follow-up and a longer
   sequence with deterministic regression and one bounded live retest.
2. **Dataset dates should be explicit.** All-history spending was numerically
   correct, but the answer said June 25–October 23. The immutable snapshot actually
   starts June 26. Supply exact start/end dates from trusted snapshot metadata
   rather than asking the model to infer them from “120 days.” Also label October
   totals as month-to-date when comparing against a complete September.
3. **Filtering currently fetches extra data.** Merchant/amount questions succeeded
   on this fixture by retrieving records and filtering inside the model. Those
   are not dedicated query arguments yet. This increases context use; it is an
   efficiency/scaling gap, not an observed incorrect answer in these trials.

Static limitations still requiring later evaluation: oversized result sets and
recovery after model-generated invalid tool arguments. The invalid-date trial
did not exercise recovery because the model asked for clarification first.
Balances, money movement and live exchange rates remain outside the read-only
banking tool capabilities.

## Evidence and cost

Persisted run IDs for the key observations:

- Typo: `8fda2e09-9432-4fc7-a02d-b55e5acac6f4`.
- Failed follow-up: `88be3a6c-327e-4833-a69e-29549371cebc`.
- Same exclusion task in a clean conversation: `5ab7c178-f762-44a2-847a-5ae166f8581a`.
- Date-label discrepancy: `fedb9acd-82c5-4d5e-8003-e1e64ed87585`.
- Browser typo: `73302bf9-7fc7-442e-a627-b8cb64b160c1`.

The local ledger records **US$0.004054** confirmed usage across funded trials
(35 model calls). Prior quota failures retain **US$0.012** uncertain reservation;
these are not confirmed charges. Remaining spendable liability is US$44.983946.
Use the ledger total: concurrent browser calls can be included in a script's
global before/after ledger delta, so those deltas are not isolated suite costs.

Raw reports are local generated artifacts under `/tmp/sentinel-t09-*`; they are
not committed. Every run retains ordered events in local SQLite. Independent
code review passed previously; the additional evidence-review agent was
unavailable, so this result review was performed directly against stored traces
and fixture facts.

T09 remains open and PR #15 stays draft until the conversation gap is corrected
and reverified. T10 has not started.
