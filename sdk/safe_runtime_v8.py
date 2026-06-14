"""Agent Trust Kernel v8 — Production Client Enforcement SDK Engine."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional
import httpx


class AtkControlPlaneException(Exception):
    """Raised for structural gateway communication or cache validation faults."""


class AtkPolicyEnforcementViolation(Exception):
    """Raised when an operation breaches declarative constitutional boundaries."""


class SafeExecutionLayerV8Client:
    def __init__(
        self, 
        agent_id: str, 
        master_secret_seed: str, 
        gateway_url: str,
        root_swarm_tx_id: Optional[str] = None,
        parent_tx_id: Optional[str] = None,
        swarm_depth: int = 0
    ):
        self.agent_id = agent_id
        self.master_secret = master_secret_seed
        self.gateway_url = gateway_url.rstrip("/")
        self.root_swarm_tx_id = root_swarm_tx_id
        self.parent_tx_id = parent_tx_id
        self.swarm_depth = swarm_depth
        self._blocked = False

    def _derive_epoch_keys(self, timestamp: int) -> list[bytes]:
        """Generates an explicit array containing past, present, and future daily keys."""
        base_epoch = timestamp // 86400
        target_windows = [base_epoch, base_epoch - 1, base_epoch + 1]
        return [
            hmac.new(
                self.master_secret.encode("utf-8"),
                f"{self.agent_id}:{epoch}".encode("utf-8"),
                hashlib.sha256
            ).digest()
            for epoch in target_windows
        ]

    def _normalize_scalar_value(self, value: Any) -> str:
        """Normalizes primitive data types to ensure identical cross-language serialization strings."""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return f"{value:g}" if isinstance(value, float) else str(value)
        if value is None:
            return "null"
        return str(value).strip()

    def _generate_canonical_signatures(
        self, nonce: str, timestamp: str, tool_name: str, intent_passport: dict, argument_keys: list[str], argument_values: list[str]
    ) -> list[str]:
        """Serializes intent maps and argument vectors into a strict newline sequence layout."""
        canonical_payload_block = "".join(
            f"{k.strip()}:{v.strip()}\n" for k, v in zip(argument_keys, argument_values)
        )
        minified_intent_json = json.dumps(intent_passport, sort_keys=True, separators=(",", ":"))
        
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{minified_intent_json}\n{canonical_payload_block.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    async def register_entity(self, owner_email: str, daily_budget_limit: float = 500.00) -> dict:
        """Lifecycle Management: Spawns the autonomous entity profile in CREATION state."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self.gateway_url}/v1/entity/register",
                json={
                    "entity_id": self.agent_id,
                    "owner_email": owner_email,
                    "daily_budget_limit": daily_budget_limit
                }
            )
            if response.status_code != 200:
                raise AtkControlPlaneException(f"Entity registration failed with status: {response.status_code}")
            return response.json()

    async def certify_entity(self, stress_test_score: float, governance_check_passed: bool) -> dict:
        """Lifecycle Management: Updates stress scores and governance clearances to promote to CERTIFIED."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self.gateway_url}/v1/entity/certify",
                json={
                    "entity_id": self.agent_id,
                    "stress_test_score": stress_test_score,
                    "governance_check_passed": governance_check_passed
                }
            )
            if response.status_code != 200:
                raise AtkControlPlaneException(f"Entity certification failed: {response.text}")
            return response.json()

    async def deploy_entity(self) -> dict:
        """Lifecycle Management: Activates the certified entity for production deployments."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self.gateway_url}/v1/entity/deploy",
                json={"entity_id": self.agent_id}
            )
            if response.status_code != 200:
                raise AtkControlPlaneException(f"Entity deployment failed: {response.text}")
            return response.json()

    async def update_genome(
        self, model_name: str, prompt_hash: str, registered_tools: list[str], memory_version: str = "v1.0.0"
    ) -> dict:
        """Entity Evolution: Tracks prompt instruction hashes and model changes over time."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{self.gateway_url}/v1/entity/genome/update",
                json={
                    "entity_id": self.agent_id,
                    "model_name": model_name,
                    "prompt_hash": prompt_hash,
                    "registered_tools": registered_tools,
                    "memory_version": memory_version
                }
            )
            if response.status_code != 200:
                raise AtkControlPlaneException(f"Entity genome update failed: {response.status_code}")
            return response.json()

    async def enforce_tool_gate(
        self, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        intent_evidence_hashes: list[str],
        estimated_cost: float = 0.001,
        causal_metadata: Optional[dict] = None
    ) -> str:
        """Phase 1: Pre-verify transaction blocks, implementing multi-layer governance primitives."""
        if self._blocked:
            raise AtkControlPlaneException("CRITICAL FAIL-CLOSED: Local engine isolated after previous fault.")

        sorted_keys = sorted(arguments.keys())
        argument_values = [self._normalize_scalar_value(arguments[k]) for k in sorted_keys]

        intent_passport = {
            "goal": intent_goal,
            "evidence": intent_evidence_hashes,
            "confidence": "1.0000"
        }
        
        swarm_governance = {
            "root_swarm_tx_id": self.root_swarm_tx_id,
            "parent_tx_id": self.parent_tx_id,
            "swarm_depth": self.swarm_depth
        }

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signatures = self._generate_canonical_signatures(
            nonce, timestamp, tool_name, intent_passport, sorted_keys, argument_values
        )

        payload = {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "argument_keys": sorted_keys,
            "argument_values": argument_values,
            "nonce": nonce,
            "timestamp": timestamp,
            "signatures": signatures,
            "estimated_cost": estimated_cost,
            "intent_passport": intent_passport,
            "swarm_governance": swarm_governance,
            "causal_metadata": causal_metadata or {}
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare", json=payload
                )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Proxy endpoint dropped context pipeline. Ref: {exc}"
                ) from exc

            if response.status_code in (401, 403, 429, 406, 500):
                raise AtkPolicyEnforcementViolation(
                    f"ACCESS DENIED: Planetary control plane protection ring block: {response.text}"
                )

            if response.status_code == 200:
                return response.json()["tx_id"]

            raise AtkControlPlaneException(f"Core execution engine returned unmapped code: {response.status_code}")

    async def resolve_tool_settlement(
        self, tx_id: str, status: str, value_created: float = 0.0, tool_output: Any = None
    ) -> None:
        """Phase 2: Finalize transaction tracking, logging economic returns and value created."""
        output_bytes = json.dumps(tool_output if tool_output is not None else {}, separators=(",", ":")).encode("utf-8")
        payload_content_hash = hashlib.sha256(output_bytes).hexdigest()

        payload = {
            "tx_id": tx_id,
            "agent_id": self.agent_id,
            "status": status,
            "payload_content_hash": payload_content_hash,
            "value_created": value_created
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/commit", json=payload
                )
                if response.status_code != 200:
                    raise AtkControlPlaneException(
                        f"Phase 2 verification node rejected settlement sequence: {response.status_code}"
                    )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger verification engine database lost sync: {exc}"
                ) from exc


class SafeTwoPhaseCommitContextV8:
    """Async context manager enforcing atomic Phase 2 commitments with economic ROI metrics."""

    def __init__(
        self, 
        client: SafeExecutionLayerV8Client, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        intent_evidence_hashes: list[str],
        estimated_cost: float = 0.001,
        causal_metadata: Optional[dict] = None
    ):
        self.client = client
        self.tool_name = tool_name
        self.arguments = arguments
        self.intent_goal = intent_goal
        self.intent_evidence_hashes = intent_evidence_hashes
        self.cost = estimated_cost
        self.causal_metadata = causal_metadata
        self.tx_id: Optional[str] = None
        self.aborted = False
        self.value_created = 0.0

    async def __aenter__(self) -> "SafeTwoPhaseCommitContextV8":
        self.tx_id = await self.client.enforce_tool_gate(
            tool_name=self.tool_name,
            arguments=self.arguments,
            intent_goal=self.intent_goal,
            intent_evidence_hashes=self.intent_evidence_hashes,
            estimated_cost=self.cost,
            causal_metadata=self.causal_metadata
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.tx_id is None:
            return False
        if exc_type is not None:
            self.aborted = True
            await self.client.resolve_tool_settlement(self.tx_id, "ABORTED", 0.0, None)
        return False

    async def commit(self, output_payload: Any, value_created: float = 0.0) -> None:
        if not self.aborted and self.tx_id:
            self.value_created = value_created
            await self.client.resolve_tool_settlement(
                self.tx_id, "COMMITTED", self.value_created, output_payload
            )
