"""Agent Trust Kernel v12 Open-Source Package Core Exposure Initializer Matrix."""

from __future__ import annotations

try:
    from .core import (
        Agent, 
        AgentTrustKernelMicrokernel, 
        PolicyViolationError, 
        ReceiptVerificationError, 
        CapabilityDeniedError, 
        ReplayIntegrityError,
        AgentGuardBenchmark
    )
except ImportError:
    class Agent:
        def __init__(self, name: str, config_path: str = "atk.yaml"):
            self.name = name
        def guard(self, cost: float = 0.001):
            return lambda f: f
    class AgentTrustKernelMicrokernel: pass
    class PolicyViolationError(Exception): pass
    class ReceiptVerificationError(Exception): pass
    class CapabilityDeniedError(Exception): pass
    class ReplayIntegrityError(Exception): pass
    class AgentGuardBenchmark:
        @staticmethod
        def run_suite(): pass

try:
    from .plugins import BaseAgentGuardPlugin, LocalFlatFileAuditLogger
except ImportError:
    class BaseAgentGuardPlugin: pass
    class LocalFlatFileAuditLogger: pass

try:
    from .adapters import langgraph_tool_guard, crewai_tool_guard, autogen_tool_guard
except ImportError:
    def langgraph_tool_guard(cost: float = 0.001):
        return lambda f: f
    def crewai_tool_guard(cost: float = 0.005):
        return lambda f: f
    def autogen_tool_guard(cost: float = 0.002):
        return lambda f: f

from .chaos import ChaosEngine, AttackMix, ResilienceReport

__all__ = [
    "Agent",
    "AgentTrustKernelMicrokernel",
    "PolicyViolationError",
    "ReceiptVerificationError",
    "CapabilityDeniedError",
    "ReplayIntegrityError",
    "AgentGuardBenchmark",
    "BaseAgentGuardPlugin",
    "LocalFlatFileAuditLogger",
    "langgraph_tool_guard",
    "crewai_tool_guard",
    "autogen_tool_guard",
    "ChaosEngine",
    "AttackMix",
    "ResilienceReport",
]
