# Sentinel implementation plan — product phases and execution order

## Product goal and complete flow

Build a banking-agent security workbench that discovers an observed failure,
investigates its cause, proposes a repair, and verifies that repair before the
engineer accepts it.

```text
Use banking assistant
→ Assess assistant
→ Attacker Agent generates an attack
→ Evidence records actual behavior
→ Investigator Agent identifies the cause
→ Defense Agent proposes a repair
→ User presses Generate Fix
→ Coding Agent patches an isolated workspace
→ Security and normal-use tests run
→ Identical attack is replayed
→ User reviews the diff and evidence
→ Accept, reject, export, or create a PR
```

**Durable product rule:** Sentinel inspects the target assistant's executable tools,
policies and data access before attacking it. The Attacker Agent creates attacks
for that target; actual execution evidence establishes whether a weakness was
observed. The Investigator Agent uses that evidence and the recorded source
revision to explain the cause. The Defense Agent reasons from the cause and
proposes a repair, rather than choosing a canned fix from a violation-to-fix map.
Only after the engineer requests **Generate Fix** does the Coding Agent create
and apply a new patch in an isolated copy of the vulnerable target. Sentinel
tests that generated patch, replays the attack, and shows its exact code diff and
results. A prebuilt protected implementation may serve as a reference or an
independent control test; it is never the Coding Agent's generated repair and
must never be substituted for that patch in a proof-of-fix report.

**Ticket numbers are identifiers—not strict execution order.** Preserve IDs for
GitHub history. Phases describe capabilities; dependencies determine execution.
See [the status tracker](docs/ROADMAP.md) and [the historical MVP plan](docs/archive/DETERMINISTIC_MVP_PLAN.md).
Below, each ticket states its explanation, technical build/purpose, visible result,
dependencies, and acceptance gate. Dependencies are ticket IDs, not phase numbers.

## 1. Trustworthy foundation — T01–T04

- **Explanation:** Establish what the assistant can do, what it actually did, and which data it may access.
- **Technical build:** Target manifests, evidence persistence, isolated bank snapshots, and trusted authorization.
- **Visible result:** Inspect real capabilities and executable access-control traces.
- **Why required:** Attacks, investigations, and repairs need accurate inputs and observations.
- **Dependencies/gate:** T01 → T02 → T03 → T04; ownership holds and evidence matches actual operations.

### T01 — Describe the actual target · Complete

- **Build/why:** Strict configuration and actual-tool manifests prevent unsupported security claims.
- **Visible:** Model-controlled arguments, trusted bindings, policy facts, and configuration digests.
- **Depends:** None. **Gate:** Schemas match tools; identity cannot be forged through target settings; unavailable controls are rejected.

### T02 — Record what actually happens

- **Build/why:** A framework-independent recorder captures operations at execution boundaries, giving future agents trustworthy observations.
- **Visible:** Ordered tool, validation, authorization, and repository traces through a read-only API.
- **Depends:** T01. **Gate:** Durable ordering, causality, stable digests, redaction, provenance, partial failures and safe migration; denials cause no successful read.

Events include run/attempt IDs, UUID event ID, sequence, UTC timestamp, typed name,
actor, sanitized structured payload, provenance, optional parent, payload digest,
and schema/redaction versions. Use observed-run/event tables separate from legacy
stories; hash canonical JSON after redaction. No normal event update/delete API.
Instrument existing tools/repository operations only. Reserve future agent event
names without manufacturing observations. No provider calls; T02 costs $0.

### T03 — Give experiments a realistic, isolated bank

- **Build/why:** Scoped queries, integer cents, varied synthetic data, snapshots and memo overlays support useful questions and repeatable attacks.
- **Visible:** Filter transactions, aggregate spending and compare periods.
- **Depends:** T01–T02. **Gate:** Independent expected calculations/date cases pass; ownership holds; overlays cannot alter shared data or another run.

### T04 — Enforce permissions outside the model

- **Build/why:** Typed tools and a policy gateway separate requested actions from application authority.
- **Visible:** Requested/effective arguments and actual permission decisions.
- **Depends:** T03. **Gate:** Protected tools omit customer IDs; malformed input stops before reads; repository checks are independent; vulnerable tools stay in the labeled lab.

T04 establishes executable target and reference-control boundaries. Selecting a
prebuilt protected profile is not a generated repair or proof that the later
Coding Agent patched the vulnerable target. In the assessment demo, the visible
assistant is the selected vulnerable synthetic lab target; Sentinel attacks that
same assistant. After “Generate Fix,” it tests a patched isolated copy of that
target. The protected profile remains a separate reference/direct-control test.
For both MVP attacks, generated repairs receive focused security and normal-use
tests plus one bounded correction attempt. A patch is never labeled fixed unless
those checks and clean replay pass.

## 2. Working banking chatbot — T05–T09

- **Explanation:** Make the banking assistant useful before assessing its security.
- **Technical build:** Shared runtime, bounded sessions, chat/inspector UI, accounting and opt-in live adapter.
- **Visible result:** Flexible read-only questions with inspectable tool activity.
- **Why required:** Assess the same assistant that people actually use.
- **Dependencies/gate:** Foundation complete; T08 precedes T09; scoped tool-backed chat with truthful fixture/live and cost labels.

### T05 — Build the shared assistant runtime

- **Build/why:** A bounded model/tool loop replaces campaign-specific response branches and serves chat, attacks, replay and benign checks.
- **Visible:** Fixture conversations return answers through actual tools.
- **Depends:** T04. **Gate:** Fake models exercise tools, limits, refusals, malformed output and errors; compare an explicit LangGraph subgraph with create_agent using a recorded fake trace.

### T06 — Support safe follow-up conversations

- **Build/why:** Server-managed identity and bounded history support follow-up reasoning without model-controlled identity.
- **Visible:** “Exclude groceries” can follow a spending question.
- **Depends:** T05. **Gate:** About five complete turns within the token cap, preserved tool pairs, isolated customers/histories and clear overflow handling.

### T07 — Put chat beside the security inspector

- **Build/why:** React connects banking answers with their underlying operations.
- **Visible:** Working chat, expandable inspector, and “Assess assistant.”
- **Depends:** T06. **Gate:** Real event links, clear loading/errors, explicit execution labels, responsive layouts and keyboard access.

### T08 — Control API spending

- **Build/why:** Durable usage and atomic reservations bound every agent and repair call.
- **Visible:** Expected/maximum cost, usage and remaining budget.
- **Depends:** T01–T02. **Gate:** Reservations, retries, uncertain charges and restarts enforce $45 USD/project and $2/assessment; all future roles use this broker.

### T09 — Connect the live model deliberately

- **Build/why:** An opt-in Responses adapter powers the same tested runtime.
- **Visible:** Live banking conversations with usage evidence.
- **Depends:** T05, T08. **Gate:** Reverify pricing/availability; explicit smoke validates tools/output; missing credentials preserve fixtures; failures never silently become scripted successes.

## 3. Attack and detection — T10–T11

- **Explanation:** Discover whether attacker-controlled banking text causes a violation.
- **Technical build:** Evidence-based deterministic scoring and bounded manifest-informed attacks.
- **Visible result:** Tailored attacks and supported findings.
- **Why required:** Repair must address an observed failure rather than an assumed weakness.
- **Dependencies/gate:** Runtime/accounting available; findings cite actual evidence and distinguish resistance, failure and insufficient evidence.

### T10 — Detect cross-customer violations with code

- **Build/why:** Score actual reads, context delivery and output instead of trusting model explanations.
- **Visible:** Show where protected information crossed a boundary.
- **Depends:** T02, T05. **Gate:** Distinguish requested access, permission, reads, context dispatch and disclosure; every finding cites valid events; missing evidence cannot pass.

### T11 — Generate attacks for this assistant

- **Build/why:** An Attacker Agent analyzes the target's real exposed capabilities through sanitized manifests/feedback and proposes structured memo attacks relevant to them.
- **Visible:** Tailored payload, objective and observed outcome.
- **Depends:** T01, T08–T10. **Gate:** Objective/channel/payload bounds and at most three attempts; feedback excludes protected values; seeds remain labeled regression fixtures.

## 4. Investigation and autonomous repair — T21–T26

- **Explanation:** Turn a supported finding into a user-requested, reviewable repair.
- **Technical build:** Investigator, Defense and Coding Agent roles, structured plans, sandbox execution, verification and revision-bound actions.
- **Visible result:** Generate a fix, inspect its diff/evidence, then accept or export it.
- **Why required:** Close the gap between finding a failure and resolving it.
- **Dependencies/gate:** Interleaves with Phase 5; only an exact verified revision can be accepted. Autonomous generation begins after “Generate Fix.”

### T21 — Investigate the cause

- **Build/why:** An Investigator Agent inspects observed evidence and bounded source snippets at the recorded revision to locate the violated trust boundary.
- **Visible:** A concise investigation links events to actual source/configuration locations.
- **Depends:** T03, T10–T11. **Gate:** References resolve at the recorded revision; facts/hypotheses are separate; explanations cannot become deterministic verdicts.

### T22 — Propose a repair

- **Build/why:** A Defense Agent reasons from the Investigator's evidence-backed cause and creates a structured RemediationPlan; no hard-coded violation-to-fix mapping selects its proposal.
- **Visible:** Cause, proposed change, expected effect, usability risks and verification requirements.
- **Depends:** T08, T21. **Gate:** Support configuration, controls/combinations and source patches; validate feasibility/scope; identify inaccessible source explicitly.

### T23 — Prepare an isolated repair workspace

- **Build/why:** A Git workspace plus restricted container protects the original checkout and host.
- **Visible:** “Generate Fix” prepares a bounded execution environment.
- **Depends:** T14, T22 and supported sandbox. **Gate:** No original-file edits, secrets, unrestricted network or arbitrary host commands; no unsafe fallback when sandbox support is missing.

### T24 — Generate and apply the candidate patch

- **Build/why:** After “Generate Fix,” a Coding Agent creates a new bounded patch for the vulnerable target; trusted code validates and applies it in the isolated workspace.
- **Visible:** Complete source/configuration diff and generation status.
- **Depends:** T08, T23. **Gate:** Enforce paths/size; prohibit scorer, evidence and verification-test edits; one candidate plus one bounded correction; record changes/failures. A prebuilt protected profile cannot stand in for the generated patch.

### T25 — Verify the candidate repair

- **Build/why:** A trusted runner tests the Coding Agent's applied patch, normal-use behavior and clean attack replay, then shows the exact diff and results.
- **Visible:** Verified, rejected or inconclusive candidate with supporting results.
- **Depends:** T12–T13, T24. **Gate:** Verify the generated patch's recorded revision and frozen attack/snapshot; reject failed tests, incomplete evidence and unexpected replay differences. Reference controls are reported separately from generated-patch verification.

### T26 — Let the engineer decide

- **Build/why:** Revision-bound actions support acceptance, rejection, export and explicit PR creation.
- **Visible:** Act on a reviewed repair without automatic production deployment.
- **Depends:** T15, T25. **Gate:** Actions reference the verified revision; stale candidates require reverification; accept selects a verified local target revision; PR creation is explicit.

## 5. Verification and polished product — T12–T16

- **Explanation:** Make every security/repair claim understandable and reproducible.
- **Technical build:** Paired runs, direct probes, benign checks, lifecycle, proof UI and regression export.
- **Visible result:** Follow a complete assessment and reproduce its evidence.
- **Why required:** Attractive UI and plausible explanations need independently inspectable proof.
- **Dependencies/gate:** Interleaves with Phase 4; complete cross-customer flow works through the UI without presenting uncertainty or incomplete work as success.

### T12 — Replay the same case cleanly

- **Build/why:** Compare independently recorded paired inputs with a candidate configuration/source revision; the mechanism later verifies a generated patch, while reference-control runs retain their own label.
- **Visible:** Isolated before/after conversations and explicit controlled-input comparison.
- **Depends:** T11, T13, T22. **Gate:** Fresh histories and identical request/payload/identity/snapshot/model settings; only declared repair differences; no automatic preset selection required.

### T13 — Check security without destroying usefulness

- **Build/why:** Reusable direct probes and real benign-agent queries test both boundaries and normal service.
- **Visible:** Separate control-test and usefulness results.
- **Depends:** T03, T05, T10. **Gate:** Exercise actual gateway/repository plus five benign queries with independent expected facts; model resistance is not enforcement proof.

### T14 — Make assessments manageable

- **Build/why:** Persisted lifecycle, cancellation and reconnectable events support long work and repair pauses.
- **Visible:** Accurate progress and “awaiting Generate Fix.”
- **Depends:** T12–T13. **Gate:** No duplicate paid work after reconnect/restart; cancellation prevents subsequent operations; retain partial evidence.

### T15 — Show a clear proof workspace

- **Build/why:** Join conversations, investigation, proposal, generated code diff, tests and evidence in one coherent interface, labeling reference controls separately.
- **Visible:** Finding → Proposed repair → Verification without requiring raw JSON.
- **Depends:** T07, T14, T21–T22, T25. **Gate:** Evidence-linked claims, visible failure/uncertainty, expandable detail, matching report/UI, accessibility and responsive review.

### T16 — Make the product reproducible and portfolio-ready

- **Build/why:** Frozen trials, regression exports, setup documentation and a guided example make results reusable.
- **Visible:** Complete walkthrough and assessment/regression artifacts.
- **Depends:** T15, T26. **Gate:** Separate adaptive/repeated trials and retain errors; clean checkout works; no-key demo uses real tools and explicitly labeled fake models.

## 6. Phishing expansion — T17–T20

- **Explanation:** Reuse the working architecture to assess malicious banking links.
- **Technical build:** Defense comparison, action provenance, exact-host policy, phishing attacks and repair verification.
- **Visible result:** Both attack families work in the same product.
- **Why required:** Demonstrate reusable engineering beyond one hard-coded story.
- **Dependencies/gate:** Complete cross-customer flow first; both families share runtime, evidence, investigation, repair and verification.

### T17 — Compare two permission defenses

- **Build/why:** Compare gateway rejection with removing customer authority from schemas.
- **Visible:** Explain differences between two enforceable controls.
- **Depends:** T16. **Gate:** Replay frozen cases, show schema/policy differences, and prevent unauthorized reads in both. This expansion comparison still concerns customer access.

### T18 — Control which links become actions

- **Build/why:** Typed provenance and exact-host HTTPS policy prevent untrusted bank actions.
- **Visible:** Link origin, decision and precise rejection reason.
- **Depends:** T05, T08. **Gate:** Cover malformed URLs, schemes, credentials, ports, IPs, Unicode and host tricks; inert prose and working approved actions.

### T19 — Generate and investigate phishing attacks

- **Build/why:** Reuse attacks, scoring, investigation and repair for malicious memo links.
- **Visible:** Phishing findings lead to supported remediation proposals.
- **Depends:** T11–T13, T18, completed repair/investigation components. **Gate:** Fail unsafe actionable recommendations, not inert warnings; minimize memo only when unnecessary; test controls before combinations.

### T20 — Finish both-family proof and regressions

- **Build/why:** Extend the existing proof UI/regressions rather than create another dashboard.
- **Visible:** Inspectable before/after proof and reusable fixtures for both families.
- **Depends:** T16, T19. **Gate:** Link proposals, provenance, decisions, delivered actions and positive controls; honest fixtures and opt-in live trials.

## Recommended execution order

```text
T01 — complete
T02 → T03 → T04
→ T05 → T06 → T07 → T08 → T09
→ T10 → T11
→ T13
→ T21 → T22
→ T12 → T14
→ T23 → T24 → T25
→ T15 → T26 → T16
→ T17 → T18 → T19 → T20
```

T13 is early because reusable tests precede repair trust. T12/T14 precede patches
because replay and state support repair execution. T15 precedes T26 so users can
review evidence before acceptance/publication.

## Delivery rules and scope

- One approved ticket, focused branch, tested PR, then protected main. Explain the
  ticket before implementation, show evidence afterward, and stop for user review.
- Preserve the selected visual direction and one consistent workspace: clear
  progress, useful defaults, expandable detail, polished failure states.
- Separate live observations, direct-control tests, model proposals and fixtures.
  Models never authorize themselves or grade their own security. Resistance alone
  cannot prove security; missing evidence/timeouts cannot prove a repair.
- Preserve $45 USD project/$2 assessment ceilings and zero-provider-call CI.
  All agent/repair calls must use the broker. Start live evidence with one trial.
- Prefer explicit Python, SQLite and existing frameworks; no distributed queues
  or generic enterprise platform. Worktrees alone are not executable-code sandboxes.
- Repair starts with the built-in source-accessible target. Black-box adapters may
  propose configuration/gateway artifacts, never claim inaccessible source edits.
- T02 implements evidence only. Chat, agents, generated patches and repair UI remain later tickets.
