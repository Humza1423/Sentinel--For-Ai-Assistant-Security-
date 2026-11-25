# T14 · Saved banking checks

Open the banking workspace, select Assess assistant, then Run banking checks. The server freezes the selected target configuration and runs five customer questions using its tools. Four separate direct checks exercise the protected reference. The screen labels fixture execution and zero API cost. Reports list actual run IDs and evidence IDs. An engineer can download the JSON.

The lifecycle is queued → running → complete, with cancelled, failed and interrupted terminal states. Each case is recorded immediately. A repeated start request with the same session/request ID returns its saved assessment. A database transaction permits one active assessment. Startup marks unfinished assessments interrupted and retains their events.

Cancellation is cooperative. Trusted checks run before each model and tool invocation, including the direct schema probe. An in-flight call can finish. Cancellation prevents subsequent operations. The test suite cancels midway through a conversation and after one saved benign result.

The events route returns a finite server-sent event page. Each event has a sequence ID. Reconnecting with Last-Event-ID retrieves only newer persisted events. Reading progress starts no new work. The UI polls status while active and restores the saved assessment when reopened.

The lifecycle currently serves fixture usefulness and reference control checks. The integrated attack/investigation/repair pipeline remains unfinished following an automatic safety-review rejection. It is explicitly absent from completion claims. The default tests make no provider calls.

## Learning notes

FastAPI accepts the request and schedules a background job. SQLite records its state and ordered progress. A context variable carries the cancellation check through the existing assistant graph. LangGraph still controls the model/tool loop. Every fixture question invokes that shared runtime, and deterministic Python checks judge the result. Durable retries, partial evidence and clear labels make the engineering result inspectable even when work stops halfway.
