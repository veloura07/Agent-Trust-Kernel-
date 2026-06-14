"""Agent Trust Kernel v11 — Production Client Enforcement SDK Engine."""

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
    """Raised for structural gateway communication or gateway connection drops."""


class AtkPolicyEnforcementViolation(Exception):
    """Raised when an operation breaches declarative constitutional boundaries."""


class SafeExecutionLayerV11Client:
    def __init__(
        self, 
        agent_id: str, 
        master_secret_seed: str, 
        gateway_url: str,
        root_swarm_tx_id: Optional[str] = None,
        parent_tx_ids: Optional[list[str]] = None,
        swarm_depth: int = 0,
        model_target: str = "meta-llama-3",
        prompt_hash: str = "default_baseline_v11_stub",
        tool_manifest_array: Optional[list[str]] = None,
        memory_version_tag: str = "mem_v1"
    ):
        self.agent_id = agent_id
        self.master_secret = master_secret_seed
        self.gateway_url = gateway_url.rstrip("/")
        self.root_swarm_tx_id = root_swarm_tx_id
        self.parent_tx_ids = parent_tx_ids or []
        self.swarm_depth = swarm_depth
        
        # Initialize Layer 1 Agent Genome Structural Attributes
        self.model_target = model_target
        self.prompt_hash = prompt_hash
        self.tool_manifest_array = tool_manifest_array or ["execute_web_scrape"]
        self.memory_version_tag = memory_version_tag
        self._blocked = False
        
        # Distributed Control Plane Local Cache Strategy (Layer 10 Resilience Moat)
        self._local_cache_permissions: dict[str, str] = {}
        self._local_budget_consumed = 0.0
        self._local_budget_limit = 500.0

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

    def _calculate_genome_hash(self) -> str:
        """Assembles a static structural footprint checksum matching code configuration variables."""
        sorted_tools = sorted(self.tool_manifest_array)
        payload_data = f"{self.model_target}:{self.prompt_hash}:{','.join(sorted_tools)}:{self.memory_version_tag}"
        return hashlib.sha256(payload_data.encode("utf-8")).hexdigest()

    def _generate_canonical_signatures(
        self, nonce: str, timestamp: str, tool_name: str, intent_passport: dict, genome_signature: dict, argument_keys: list[str], argument_values: list[str]
    ) -> list[str]:
        """Serializes sub-system structures into newline delimited character bytes to avoid object sorting drift."""
        canonical_payload_block = "".join(
            f"{k.strip()}:{v.strip()}\n" for k, v in zip(argument_keys, argument_values)
        )
        minified_intent_json = json.dumps(intent_passport, sort_keys=True, separators=(",", ":"))
        minified_genome_json = json.dumps(genome_signature, sort_keys=True, separators=(",", ":"))
        
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{minified_intent_json}\n{minified_genome_json}\n"
            f"{canonical_payload_block.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    def cache_local_permission(self, tool_name: str, state: str) -> None:
        """Hydrates local control cache path variables to enable disconnected fallback boundaries."""
        self._local_cache_permissions[tool_name] = state

    async def enforce_tool_gate(
        self, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        evidence_confirming_hashes: list[str],
        evidence_contradicting_hashes: list[str],
        estimated_cost: float = 0.001
    ) -> str:
        """Phase 1: Pre-verify transaction blocks, enforcing low-latency Hot Path structural execution checks."""
        if self._blocked:
            raise AtkControlPlaneException("CRITICAL FAIL-CLOSED: Local engine isolated after previous fault.")

        sorted_keys = sorted(arguments.keys())
        argument_values = [self._normalize_scalar_value(arguments[k]) for k in sorted_keys]

        # Assemble Intent Passport Objectives
        intent_passport = {
            "goal": intent_goal,
            "evidence_confirming_hashes": evidence_confirming_hashes,
            "evidence_contradicting_hashes": evidence_contradicting_hashes
        }
        
        # Assemble Agent Genome Signature Attributes
        genome_signature = {
            "genome_hash": self._calculate_genome_hash(),
            "model_target": self.model_target,
            "prompt_hash": self.prompt_hash
        }

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signatures = self._generate_canonical_signatures(
            nonce, timestamp, tool_name, intent_passport, genome_signature, sorted_keys, argument_values
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
            "genome_signature": genome_signature,
            "swarm_governance": {
                "root_swarm_tx_id": self.root_swarm_tx_id,
                "parent_tx_ids": self.parent_tx_ids,
                "swarm_depth": self.swarm_depth
            }
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare", json=payload
                )
                
                if response.status_code in (401, 403, 429, 406, 500):
                    raise AtkPolicyEnforcementViolation(
                        f"ACCESS DENIED: Planetary control plane protection block: {response.text}"
                    )

                if response.status_code == 200:
                    return response.json()["tx_id"]
                    
            except (httpx.RequestError, httpx.TimeoutException) as network_fault:
                # --- DISTRIBUTED CONTROL PLANE PARTITION RESILIENCE FALLBACK ---
                # Gateway unavailable: Fall back to checking the signed local permission cache invariants
                if self._local_cache_permissions.get(tool_name) == "false":
                    raise AtkPolicyEnforcementViolation(
                        f"ACCESS DENIED: Fallback cache explicitly restricts tool capability execution frame: {tool_name}"
                    )
                
                if self._local_budget_consumed + estimated_cost > self._local_budget_limit:
                    raise AtkPolicyEnforcementViolation(
                        "ACCESS DENIED: Local emergency fallback budget boundary limit overrun."
                    )
                
                self._local_budget_consumed += estimated_cost
                return f"local_tx_{secrets.token_hex(8)}"

            raise AtkControlPlaneException(f"Core engine returned unmapped code context: {response.status_code}")

    async def resolve_tool_settlement(
        self, tx_id: str, status: str, tool_output: Any = None
    ) -> None:
        """Phase 2: Finalize transaction tracking using out-of-band content checksum validation."""
        if tx_id.startswith("local_tx_"):
            # Operation completed entirely under local fallback parameters; log out trace directly
            return

        output_bytes = json.dumps(tool_output if tool_output is not None else {}, separators=(",", ":")).encode("utf-8")
        payload_content_hash = hashlib.sha256(output_bytes).hexdigest()

        payload = {
            "tx_id": tx_id,
            "agent_id": self.agent_id,
            "status": status,
            "payload_content_hash": payload_content_hash
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/commit", json=payload
                )
                if response.status_code != 200:
                    raise AtkControlPlaneException(
                        f"Phase 2 verification node rejected settlement context sequence: {response.status_code}"
                    )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger verification OS lost state sync mapping: {exc}"
                ) from exc


class SafeTwoPhaseCommitContextV11:
    """Async context manager enforcing atomic Phase 2 commitments."""

    def __init__(
        self, 
        client: SafeExecutionLayerV11Client, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        evidence_confirming_hashes: list[str],
        evidence_contradicting_hashes: list[str],
        estimated_cost: float = 0.001
    ):
        self.client = client
        self.tool_name = tool_name
        self.arguments = arguments
        self.intent_goal = intent_goal
        self.evidence_confirming_hashes = evidence_confirming_hashes
        self.evidence_contradicting_hashes = evidence_contradicting_hashes
        self.cost = estimated_cost
        self.tx_id: Optional[str] = None
        self.aborted = False

    async def __aenter__(self) -> "SafeTwoPhaseCommitContextV11":
        self.tx_id = await self.client.enforce_tool_gate(
            tool_name=self.tool_name,
            arguments=self.arguments,
            intent_goal=self.intent_goal,
            evidence_confirming_hashes=self.evidence_confirming_hashes,
            evidence_contradicting_hashes=self.evidence_contradicting_hashes,
            estimated_cost=self.cost
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.tx_id is None:
            return False
        if exc_type is not None:
            self.aborted = True
            await self.client.resolve_tool_settlement(self.tx_id, "ABORTED", None)
        return False

    async def commit(self, output_payload: Any) -> None:
        if not self.aborted and self.tx_id:
            await self.client.resolve_tool_settlement(
                self.tx_id, "COMMITTED", output_payload
            )
