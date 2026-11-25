"""Cooperative cancellation between bounded operations."""

from contextvars import ContextVar

on_run_started = ContextVar("sentinel_run_started", default=lambda run_id: None)

check_execution = ContextVar("sentinel_execution_check", default=lambda: None)


class ExecutionCancelled(RuntimeError):
    pass
