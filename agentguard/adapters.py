"""AgentGuard Drop-In Interceptor Adapters for Major Framework Swarms."""

from __future__ import annotations

from typing import Any, Callable, Coroutine
from .core import Agent

# Initialize corporate framework baseline singleton context instance
_global_runtime_guard_agent = Agent(name="framework_swarm_interceptor_node")


def langgraph_tool_guard(cost: float = 0.001):
    """Drop-in decorator boundary targeting LangGraph state tool functions components."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        return _global_runtime_guard_agent.guard(cost=cost)(func)
    return decorator


def crewai_tool_guard(cost: float = 0.005):
    """Drop-in decorator boundary targeting CrewAI specialized autonomous worker agents tasks."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        return _global_runtime_guard_agent.guard(cost=cost)(func)
    return decorator


def autogen_tool_guard(cost: float = 0.002):
    """Drop-in decorator boundary targeting AutoGen conversable multi-agent simulation routines."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        return _global_runtime_guard_agent.guard(cost=cost)(func)
    return decorator
