"""AgentGuard Plugins Interface."""

from __future__ import annotations
import abc
from typing import Any

class BaseAgentGuardPlugin(abc.ABC):
    @abc.abstractmethod
    async def process_event(self, event_step: str, metadata: dict[str, Any]) -> None:
        """Triggers out-of-band analytics."""

class LocalFlatFileAuditLogger(BaseAgentGuardPlugin):
    def __init__(self, log_path: str = "agentguard_audit.log"):
        self.log_path = log_path

    async def process_event(self, event_step: str, metadata: dict[str, Any]) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{event_step}] {metadata}\n")
