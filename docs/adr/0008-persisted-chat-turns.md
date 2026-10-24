# ADR 0008 — Persist complete chat turns in SQLite

Use SQLAlchemy sessions/turns around the existing LangGraph runtime. A second
graph checkpointer would duplicate persistence and complicate evidence ownership.
The server owns customer/target bindings; the browser sends only a message and
idempotency ID. An opaque HttpOnly cookie scopes local transcript/event access.
This is synthetic local identity, not production authentication.

Store full completed message/tool pairs and validate their digest against the
source output event before reuse. Dispatch evidence references original prepared
results instead of pretending history caused new repository reads. Keep five
complete turns, dropping oldest turns to satisfy a conservative 12,000-unit input
bound. UTF-8 bytes plus framing conservatively bound offline serialized input;
T09 must additionally enforce provider token counts including its wire schema.

Claim one request per session in SQLite, then release the transaction before
execution. Duplicate request IDs return saved results. Interrupted work requires
an explicit new request; startup never automatically repeats model calls. Local
process ownership prevents recovery from releasing another running worker's claim.
