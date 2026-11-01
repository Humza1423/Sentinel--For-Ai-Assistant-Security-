# T11 — Give the attacker one controlled way to test the assistant

The attacker can write a synthetic transfer memo, just as a counterparty could
write transfer text in a real banking workflow. The attacker cannot change the
assistant's instructions, tools, customer identity or database.

```text
resolved assistant → allowlisted tool surface → candidate memo
→ strict validation → owned transfer overlay → fresh assistant run
→ exact memo delivered? → T10 evidence verdict → sanitized feedback
```

`app/attack.py` owns the surface, candidate contract, provider interface and
bounded trial loop. It uses `resolve_target` to inspect actual executable tools,
`SnapshotBankRepository` for an isolated memo overlay, `run_assistant` for the
same LangGraph/LangChain runtime as chat, and `score_cross_customer_run` for a
code-based verdict. `app/runtime.py` records the actual memo digest in the tool
result prepared for model context. `app/observed_scoring.py` checks the
persisted overlay and resolved target digest before attributing an output
marker to protected data. `app/live_model.py` meters attacker calls through the
same broker as target calls, under role `attacker`.

The model chooses memo wording and may request target tools. Trusted Python
chooses the writable record, validates the candidate, enforces attempt and
budget limits, and scores events. There is no new LangGraph campaign node in
this ticket; T12 will orchestrate paired runs. Each attack attempt starts with
empty chat history and a fresh model instance.

Interpret results carefully:

- `seed_fixture` and `fake_attacker` are offline fixtures, not live model evidence.
- `live_attacker` means the candidate came from a metered live model; the
  `target_mode` field separately identifies whether the tested assistant was live.
- `not_exposed` means the memo did not reach the target model. It says nothing
  about resistance.
- An exposed `no_violation_observed` means no defined violation occurred in
  that trial. A violation cites read, context and output event IDs.
- Invalid candidates consume attempts. Provider errors stop; no result is
  silently converted into success.

Focused tests cover sanitization, scope rejection, bounded attempts, feedback,
overlay isolation, exact memo exposure, marker-source limits and a brokered
Responses mock. The normal suite uses no paid provider calls.

Interview explanation: “I derived an attacker view from the assistant's real
tool schemas, let a bounded agent propose only memo text, and ran that memo
through the same assistant as chat. I checked that the memo actually reached
the model before interpreting the security verdict.”
