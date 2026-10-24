# T08 — spending admitted before execution

`UsageBroker.execute` validates a CallPlan, reserves its conservative cost under
both ceilings, invokes a trusted injected operation and settles actual Usage.
SQLite owns admission, not an agent. Targets, attackers and future repair roles
share the same account. Charge rows retain role, plan, run/assessment correlation,
time, usage, price version, provider request ID and confirmed/uncertain status.

The usage API and BudgetPanel show recorded costs, outstanding reservations and
remaining balance. An unknown prior balance stays visibly unknown. Initialize
once with `python -m app.budget --prior-spend-usd AMOUNT` after checking earlier
project spend. No initialization or provider execution occurred during T08.

Tests use fake operations and cover exact partition/rounding arithmetic,
idempotency, simultaneous admissions, both ceilings, retry liability, restarts,
missing usage, price expiry, adapter overruns and preservation of migrated data.
T09 still needs to normalize actual Responses usage, enforce wire token limits,
disable SDK retries and run the first explicitly authorized connectivity check.

Interview explanation: “The application reserves worst-case cost before each
model call. If billing is uncertain, the reservation survives restart, so a failed
request cannot silently restore money that may already have been spent.”
