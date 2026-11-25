# ADR 0016 · Bind investigations to observed calls and the executed source

Looking up a line in today's checkout could attach the wrong code to yesterday's run. Copying the full repository into every report would preserve unrelated files and increase storage. For the built-in Python assistant, record the Git revision and digest of reviewed target files with the request. Verify startup and on-disk file contents against Git. Resolve bounded snippets from that revision when explaining a finding. A missing revision leaves the event-backed findings available.

Use the existing deterministic scorer and evidence ledger. A single optional model call interprets a curated packet. An extra agent loop would add cost without adding observations. The reporter accepts citations only from the supplied source and required chain. A human reviews the hypothesis. Generated fixes and tests of those fixes belong to subsequent tickets.
