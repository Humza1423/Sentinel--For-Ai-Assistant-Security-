# T04 decision brief — executable tool boundaries

Status: approved design, implemented in T04. This brief records the decision.

## Purpose

Give Sentinel an honest, executable boundary between a model's proposed tool
call and the bank data it can read. This prepares the same target tools for the
shared assistant runtime in T05 and produces evidence for later assessments.

Today `BankRepository.get_for(..., vulnerable=True)` puts the synthetic lab
bypass on the general repository. The current protected LangChain tool binds a
customer ID in a closure, while T03's richer snapshot queries are not yet
exposed as tools. T01 manifests reflect the current one-tool profiles, and T02
records requests and reads. T04 should connect these layers without altering the
scripted campaign's historical results.

## Options

1. Keep permission decisions inside each tool closure. This changes fewer files,
   but duplicates checks as new banking tools arrive and makes the evidence
   boundary inconsistent.
2. Use a small Python gateway with two reviewed tool profiles. It validates
   requested arguments, obtains identity from trusted `RequestContext`, records
   the decision and effective scope, and invokes the scoped repository. This
   gives each future tool the same security boundary without a generic policy
   engine. **Recommended.**
3. Adopt a general authorization framework now. It adds configuration and
   indirection without improving the two banking cases in this MVP.

## Proposed design

```text
Model-proposed typed call
→ StrictBankTool input validation
→ small gateway: reviewed profile + trusted RequestContext
→ allow/deny and effective-argument evidence
→ protected SnapshotBankRepository or named synthetic lab repository
→ actual read/result evidence
→ tool response
```

- The normal protected profile exposes narrow read-only operations from T03
  (transaction detail/list with bounded filters, spending totals and period
  comparison). Its schemas contain filters, never `customer_id`. The gateway
  supplies the trusted session identity, and the snapshot repository checks
  ownership independently.
- The explicitly named vulnerable lab profile exposes the controlled foreign
  customer lookup needed for the attack target. Move its deliberate bypass into
  `VulnerableLabBankRepository`; remove the general `vulnerable=True` switch from
  the ordinary repository. Keep legacy scripted results available through a
  small compatibility path until later tickets replace the campaign runtime.
- A memo-reading tool applies the run's overlay before returning the memo, so a
  later attacker payload reaches the target in a real tool result. Memo
  provenance remains `external_untrusted`.
- The target factory chooses a reviewed profile and derives the manifest from
  the actual tool schemas and policy. In the assessment demo, the visible chat
  uses the selected vulnerable lab target, and Sentinel attacks that same target
  through the shared runtime. The protected profile is selected only for a
  separate reference or direct-control test.
- After “Generate Fix,” the later repair workflow must patch an isolated copy
  of that selected vulnerable target and run focused security, replay and
  normal-use checks for both MVP attacks, with one bounded correction attempt.
  It may label a patch fixed only when those checks pass. T04 prepares the
  executable boundary; patch generation and verification remain later tickets.
- The protected profile is a reference and direct-control test. T04 does not
  generate a repair, claim that switching profiles patched code, or build the
  Attacker/Investigator/Defense/Coding Agents. The later Coding Agent must create
  a new patch to the vulnerable target in an isolated workspace.
- Emit requested arguments, validated arguments, trusted identity, effective
  scope, authorization decision, repository read, record ownership and errors.
  Do not record model-context delivery until the runtime actually dispatches it.

## Files expected

- `backend/app/bank.py`: separate safe and lab repository paths; retain legacy
  demo compatibility where necessary.
- `backend/app/assistant.py`: reviewed typed tools and strict invocation hook.
- `backend/app/targets.py` and, if needed, `backend/app/target_contracts.py`:
  resolve the executable profile and accurate manifest.
- `backend/app/gateway.py` (small new module if it reduces duplication): one
  authorization/invocation boundary.
- Focused backend tests plus ADR, learning note, roadmap and changelog updates.
  No database migration or frontend change is expected.

## Acceptance gate

1. Protected schemas expose no customer ID. Unknown or forged arguments fail
   before authorization and cause zero repository reads.
2. Valid protected calls return only the authenticated customer's records from
   the frozen snapshot. Guessed foreign transaction IDs return no protected data.
3. Evidence correlates the request, validation, decision, effective scope and
   actual repository result. A denied call has no successful read event.
4. The named lab profile alone can reproduce the controlled foreign lookup;
   its manifest exposes that capability honestly.
5. Invalid profile/policy combinations fail closed. Existing campaign, T01,
   T02 and T03 tests continue to pass with no provider calls.

## Main risk and resolution

Legacy demo code and tests still call the old repository methods. Replace the
shared boolean bypass carefully while preserving that demo's output. T04's new
profile must read T03 snapshots and overlays; T05 will supply the model loop.
Keep the gateway small and operation-specific rather than inventing a universal
authorization language.
