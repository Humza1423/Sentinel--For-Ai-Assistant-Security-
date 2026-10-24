"""Offline demonstration model: limited intents, actual tool-backed answers."""

import json
from typing import get_args
from uuid import uuid4

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from .bank import TransactionCategory

CATEGORIES = get_args(TransactionCategory)


class BankingFixtureModel(FakeMessagesListChatModel):
    """T09 can replace this injection point without changing the assistant graph."""

    responses: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        question = next(
            m.content.lower() for m in reversed(messages) if isinstance(m, HumanMessage)
        )
        if "exclude" in question and not any(c in question for c in CATEGORIES):
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content=json.dumps(
                                {
                                    "kind": "refusal",
                                    "display_text": "Name a supported category to exclude, such as groceries or dining.",
                                    "transaction_ids": [],
                                }
                            )
                        )
                    )
                ]
            )
        if isinstance(messages[-1], ToolMessage):
            raw = messages[-1].content
            try:
                data = json.loads(raw)
            except ValueError:
                data = None
            ids = []
            if isinstance(data, list):
                ids = [item["transaction_id"] for item in data[:5]]
                if any(word in question for word in ("spend", "spent", "grocer", "exclude")):
                    rows = [r for r in data if r["category"] not in ("income", "transfer")]
                    if "exclude" in question:
                        rows = [r for r in rows if r["category"] != "groceries"]
                    total = -sum(r["amount_cents"] for r in rows)
                    text = f"Spending in the returned period: CAD {total / 100:.2f}."
                else:
                    text = (
                        "\n".join(
                            f"{r['date']} · {r['merchant']} · CAD {r['amount_cents'] / 100:.2f}"
                            for r in data[:5]
                        )
                        or "No matching transactions."
                    )
            elif isinstance(data, dict) and "spent_cents" in data:
                results = []
                for message in reversed(messages):
                    if isinstance(message, HumanMessage):
                        break
                    if isinstance(message, ToolMessage):
                        results.append(json.loads(message.content)["spent_cents"])
                total = results[-1] - results[0] if len(results) == 2 else results[0]
                text = f"Spending from June 26 to October 23, 2026: CAD {total / 100:.2f}."
            elif isinstance(data, dict) and "transaction_id" in data:
                ids = [data["transaction_id"]]
                text = f"{data['merchant']} · CAD {data['amount_cents'] / 100:.2f}. Memo: {data['memo']['text']}"
            else:
                text = raw
            response = AIMessage(
                content=json.dumps({"kind": "answer", "display_text": text, "transaction_ids": ids})
            )
        else:
            name = "list_my_transactions"
            args = {"limit": 5}
            if any(word in question for word in ("spend", "spent", "grocer", "exclude")):
                name = "summarize_my_spending"
                args = {"start_date": "2026-06-26", "end_date": "2026-10-23"}
                for category in CATEGORIES:
                    if category in question:
                        args["category"] = category
                        break
                if "exclude" in question:
                    args.pop("category", None)
            elif any(word in question for word in ("latest", "transfer", "memo")):
                args = {"limit": 1}
                if "transfer" in question:
                    args["category"] = "transfer"
            elif not any(word in question for word in ("transaction", "show", "recent")):
                return ChatResult(
                    generations=[
                        ChatGeneration(
                            message=AIMessage(
                                content=json.dumps(
                                    {
                                        "kind": "refusal",
                                        "display_text": "Fixture mode supports recent transactions, latest transfer, spending and ‘exclude groceries’. Live language understanding arrives with the live adapter.",
                                        "transaction_ids": [],
                                    }
                                )
                            )
                        )
                    ]
                )
            response = AIMessage(
                content="", tool_calls=[{"name": name, "args": args, "id": str(uuid4())}]
            )
            if "exclude" in question and name == "summarize_my_spending":
                response.tool_calls.append(
                    {
                        "name": name,
                        "args": {
                            **args,
                            "category": next((c for c in CATEGORIES if c in question), "groceries"),
                        },
                        "id": str(uuid4()),
                        "type": "tool_call",
                    }
                )
        return ChatResult(generations=[ChatGeneration(message=response)])
