# T06 — remembered banking conversations

The chat service binds a session to its selected target and synthetic customer.
Each message runs the T05 graph with T04 tools and creates a new T02 evidence run.
SQLite stores complete turns; the history loader verifies source evidence and
preserves tool pairs before the model can see them again. Full transcripts stay
stored even when old turns leave the bounded model context.

`chat.py` owns sessions, history and request claims. `chat_api.py` defines strict
HTTP inputs. `runtime.py` still owns model/tool routing; Python still owns
identity, limits and permissions. `fixture_model.py` supports explicit offline
examples using actual bank reads; it is not general language understanding.
T09 will replace model injection with the brokered live adapter.

Tests cover follow-ups, idempotent requests, session/event privacy, real tool
execution, history tampering, trimming, busy requests, input overflow and model
setup failures. Existing migrations and legacy campaigns continue to work.

Interview explanation: “I persisted complete agent turns with evidence references,
so follow-up questions reuse verified tool data without giving the model control
of identity. The session service and security campaigns share one runtime.”
