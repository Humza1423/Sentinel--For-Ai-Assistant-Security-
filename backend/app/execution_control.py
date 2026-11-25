"""Cooperative cancellation between bounded operations."""

from contextvars import ContextVar

check_execution = ContextVar("sentinel_execution_check", default=lambda: None)


class ExecutionCancelled(RuntimeError):
    pass
