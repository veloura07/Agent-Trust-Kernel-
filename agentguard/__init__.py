"""AgentGuard — Open Source Security and Governance Runtime for AI Agents."""

from __future__ import annotations

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

from agentguard.plugins import (
    BaseAgentGuardPlugin,
    LocalFlatFileAuditLogger,
)

from agentguard.adapters import (
    langgraph_tool_guard,
    crewai_tool_guard,
    autogen_tool_guard,
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
]

__version__ = "12.0.0"
