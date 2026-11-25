# ADR 0019 · Compare independent runtime receipts

T12 began with a read-only comparison of two chat turns. Assessment execution needs to create a frozen case twice. Reusing one response or hashing the caller's case twice would only verify the caller's object. Instead, each invocation of the existing assistant runtime records what it received, then a small Python service compares the two runs.

Use the shared LangGraph assistant to perform each execution. The coordinator adds no second graph and does not choose a defense. Exact top-level configuration differences must be declared, model settings remain fixed, and prebuilt policy/tool changes are labeled reference controls. Fresh model instances and histories prevent baseline conversation contamination. The memo overlay IDs differ, while the recorded memo contents match. A matched comparison describes controlled inputs; failed runs and benign/control evaluation remain separate evidence.
