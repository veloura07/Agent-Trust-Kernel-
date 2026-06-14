"""Decorator wrapping agent tools with SEL v3 two-phase commit."""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, TypeVar

from sel_v3.client import SELClient

F = TypeVar("F", bound=Callable[..., Any])


def sel_guard(
    client: SELClient,
    tool_name: str | None = None,
    cost: float = 0.001,
) -> Callable[[F], F]:
    """Wrap a tool function with authorize → execute → settle lifecycle."""

    def decorator(fn: F) -> F:
        resolved_tool = tool_name or fn.__name__

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = inspect.signature(fn).bind_partial(*args, **kwargs)
            bound.apply_defaults()
            tool_args = dict(bound.arguments)

            with client.guard(resolved_tool, tool_args, cost):
                return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
