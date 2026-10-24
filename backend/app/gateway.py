"""Small trusted boundary between proposed banking tools and repository access."""

from collections.abc import Iterator
from contextlib import contextmanager

from .evidence import child_scope, emit
from .target_contracts import RequestContext


@contextmanager
def authorize_bank_read(
    context: RequestContext, *, profile: str, requested_customer_id: str | None = None
) -> Iterator[str]:
    """Return the effective scope for one reviewed synthetic profile."""
    if profile == "session_bound_v1":
        if requested_customer_id is not None:
            emit(
                "authorization.decided",
                "tool",
                {
                    "decision": "denied",
                    "reason_code": "model_customer_id_forbidden",
                    "authenticated_customer_id": context.authenticated_customer_id,
                    "requested_customer_id": requested_customer_id,
                },
                provenance={"authenticated_customer_id": "system_trusted"},
            )
            raise PermissionError("Customer identity is bound to the session")
        effective = context.authenticated_customer_id
        reason = "session_bound_tool"
        origin = "trusted_session"
    elif profile == "vulnerable_lookup_v1":
        if requested_customer_id is None:
            raise ValueError("Lab lookup requires a requested customer")
        effective = requested_customer_id
        reason = "deliberate_vulnerable_lab_policy"
        origin = "model_argument"
    else:
        raise ValueError("Unknown bank tool profile")

    decision = emit(
        "authorization.decided",
        "tool",
        {
            "decision": "allowed",
            "reason_code": reason,
            "authenticated_customer_id": context.authenticated_customer_id,
            "requested_customer_id": requested_customer_id,
        },
        provenance={
            "authenticated_customer_id": "system_trusted",
        },
    )
    with child_scope(decision):
        arguments = emit(
            "tool.effective_arguments",
            "tool",
            {
                "effective_customer_id": effective,
                "identity_source": origin,
            },
            provenance={"effective_customer_id": "system_trusted"}
            if origin == "trusted_session"
            else {},
        )
        with child_scope(arguments):
            yield effective
