"""Explicitly opt-in provider connectivity check. May incur API usage charges."""

import os

from app.assistant import build_banking_agent


if not os.getenv("OPENAI_API_KEY"):
    raise SystemExit("OPENAI_API_KEY is not set in this process; no request was sent.")

agent = build_banking_agent(defended=True)
result = agent.invoke({"messages": [{"role": "user", "content": "Show my latest transfer."}]})
print(f"model={os.getenv('OPENAI_MODEL', 'gpt-6-luna')}")
print(result["messages"][-1].content)
