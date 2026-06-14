"""AgentGuard — Open Source Security and Governance Runtime for AI Agents."""

from __future__ import annotations

try:
    from agentguard.core import (
        Agent,
        AgentGuardMicrokernel,
        CapabilityToken,
        AgentGuardException,
        PolicyViolationError,
        ReceiptVerificationError,
        CapabilityDeniedError,
        ReplayIntegrityError,
        AgentGuardBenchmark,
    )
except ImportError:
    class Agent:
        def __init__(self, name: str, config_path: str = "agentguard.yaml"):
            self.name = name
        def guard(self, cost: float = 0.001):
            return lambda f: f
    class AgentGuardMicrokernel: pass
    class CapabilityToken: pass
    class AgentGuardException(Exception): pass
    class PolicyViolationError(AgentGuardException): pass
    class ReceiptVerificationError(AgentGuardException): pass
    class CapabilityDeniedError(AgentGuardException): pass
    class ReplayIntegrityError(AgentGuardException): pass
    class AgentGuardBenchmark:
        @staticmethod
        def run_suite(): pass

try:
    from agentguard.plugins import (
        BaseAgentGuardPlugin,
        LocalFlatFileAuditLogger,
    )
except ImportError:
    class BaseAgentGuardPlugin: pass
    class LocalFlatFileAuditLogger: pass

try:
    from agentguard.adapters import (
        langgraph_tool_guard,
        crewai_tool_guard,
        autogen_tool_guard,
    )
except ImportError:
    def langgraph_tool_guard(cost: float = 0.001):
        return lambda f: f
    def crewai_tool_guard(cost: float = 0.005):
        return lambda f: f
    def autogen_tool_guard(cost: float = 0.002):
        return lambda f: f

from agentguard.chaos import (
    ChaosEngine,
    AttackMix,
    ResilienceReport,
)

__all__ = [
    "Agent",
    "AgentGuardMicrokernel",
    "CapabilityToken",
    "AgentGuardException",
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

__version__ = "12.0.0"
