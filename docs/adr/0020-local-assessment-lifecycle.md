# ADR 0020 · Persist local evaluation progress

An in-memory task dictionary loses reports after restart. A distributed job queue adds operational work to a single-user local application. Use two small SQLite tables for assessment state and ordered events, with a FastAPI background worker and explicit interrupted recovery. A transaction claims queued work and prevents a second active assessment. Never resume interrupted execution automatically.

Progress is stored per completed case using evaluator callbacks. Cancellation checks at the model and tool entry points stop subsequent operations. The service exposes only fixture banking evaluations and reference control probes. The attack and repair lifecycle is pending. Polling status plus finite SSE pages keeps reconnection simple and avoids long-lived worker threads.
