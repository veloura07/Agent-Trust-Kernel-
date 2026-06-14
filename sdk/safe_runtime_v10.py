"""Agent Trust Kernel v10 — Asynchronous Production Lifecycle OS SDK Engine Unit."""

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


class SafeExecutionLayerV10Client:
    def __init__(
        self, 
        agent_id: str, 
        master_secret_seed: str, 
        gateway_url: str,
        root_swarm_tx_id: Optional[str] = None,
        parent_tx_id: Optional[str] = None,
        swarm_depth: int = 0,
        model_target: str = "meta-llama-3",
        prompt_hash: str = "default_baseline_v10_stub",
        tool_manifest_array: Optional[list[str]] = None,
        memory_version_tag: str = "mem_v1"
    ):
        self.agent_id = agent_id
        self.master_secret = master_secret_seed
        self.gateway_url = gateway_url.rstrip("/")
        self.root_swarm_tx_id = root_swarm_tx_id
        self.parent_tx_id = parent_tx_id
        self.swarm_depth = swarm_depth
        
        # Initialize Layer 1 Agent Genome Structural Attributes
        self.model_target = model_target
        self.prompt_hash = prompt_hash
        self.tool_manifest_array = tool_manifest_array or ["execute_web_scrape"]
        self.memory_version_tag = memory_version_tag
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

    def _calculate_genome_hash(self) -> str:
        """Assembles a static structural footprint checksum matching code configuration variables."""
        sorted_tools = sorted(self.tool_manifest_array)
        payload_data = f"{self.model_target}:{self.prompt_hash}:{','.join(sorted_tools)}:{self.memory_version_tag}"
        return hashlib.sha256(payload_data.encode("utf-8")).hexdigest()

    def _generate_canonical_signatures(
        self, nonce: str, timestamp: str, tool_name: str, intent_passport: dict, causality_metadata: dict, genome_signature: dict, argument_keys: list[str], argument_values: list[str]
    ) -> list[str]:
        """Serializes sub-system structures into newline delimited character bytes to avoid object sorting drift."""
        canonical_payload_block = "".join(
            f"{k.strip()}:{v.strip()}\n" for k, v in zip(argument_keys, argument_values)
        )
        
        minified_intent_json = json.dumps(intent_passport, sort_keys=True, separators=(",", ":"))
        minified_causality_json = json.dumps(causality_metadata, sort_keys=True, separators=(",", ":"))
        minified_genome_json = json.dumps(genome_signature, sort_keys=True, separators=(",", ":"))
        
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{minified_intent_json}\n{minified_causality_json}\n{minified_genome_json}\n"
            f"{canonical_payload_block.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    async def enforce_tool_gate(
        self, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        evidence_confirming_hashes: list[str],
        evidence_contradicting_hashes: list[str],
        decided_by_agent_id: str,
        beneficiary_id: str,
        estimated_cost: float = 0.001
    ) -> str:
        """Phase 1: Pre-verify transaction blocks, enforcing strict multi-layer structural OS checks."""
        if self._blocked:
            raise AtkControlPlaneException("CRITICAL FAIL-CLOSED: Local engine isolated after previous fault.")

        sorted_keys = sorted(arguments.keys())
        argument_values = [self._normalize_scalar_value(arguments[k]) for k in sorted_keys]

        # Assemble Layer 3 Intent & Evidence Object Context Structures
        intent_passport = {
            "goal": intent_goal,
            "evidence_confirming_hashes": evidence_confirming_hashes,
            "evidence_contradicting_hashes": evidence_contradicting_hashes
        }
        
        # Assemble Layer 9 Swarm & Causality Trace Mappings
        causality_metadata = {
            "root_swarm_tx_id": self.root_swarm_tx_id,
            "parent_tx_id": self.parent_tx_id,
            "swarm_depth": self.swarm_depth,
            "decided_by_agent_id": decided_by_agent_id,
            "beneficiary_id": beneficiary_id
        }

        # Assemble Layer 1 Genome Trace Fingerprint Mappings
        genome_signature = {
            "genome_hash": self._calculate_genome_hash(),
            "model_target": self.model_target,
            "prompt_hash": self.prompt_hash
        }

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signatures = self._generate_canonical_signatures(
            nonce, timestamp, tool_name, intent_passport, causality_metadata, genome_signature, sorted_keys, argument_values
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
            "swarm_governance": causality_metadata,
            "genome_signature": genome_signature,
            "causality_metadata": causality_metadata
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare", json=payload
                )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Proxy endpoint dropped context pipeline connection. Ref: {exc}"
                ) from exc

            if response.status_code in (401, 403, 429, 406, 500):
                raise AtkPolicyEnforcementViolation(
                    f"ACCESS DENIED: Planetary Lifecycle OS protection ring block: {response.text}"
                )

            if response.status_code == 200:
                return response.json()["tx_id"]

            raise AtkControlPlaneException(f"Core execution engine returned unmapped code context: {response.status_code}")

    async def resolve_tool_settlement(
        self, tx_id: str, status: str, tool_output: Any = None
    ) -> None:
        """Phase 2: Finalize transaction tracking using out-of-band content checksum validation."""
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
                        f"Phase 2 verification node rejected settlement sequence: {response.status_code}"
                    )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger verification OS lost state sync mapping: {exc}"
                ) from exc


class SafeTwoPhaseCommitContextV10:
    """Async context manager enforcing atomic Phase 2 commitments."""

    def __init__(
        self, 
        client: SafeExecutionLayerV10Client, 
        tool_name: str, 
        arguments: dict[str, Any], 
        intent_goal: str,
        evidence_confirming_hashes: list[str],
        evidence_contradicting_hashes: list[str],
        decided_by_agent_id: str,
        beneficiary_id: str,
        estimated_cost: float = 0.001
    ):
        self.client = client
        self.tool_name = tool_name
        self.arguments = arguments
        self.intent_goal = intent_goal
        self.evidence_confirming_hashes = evidence_confirming_hashes
        self.evidence_contradicting_hashes = evidence_contradicting_hashes
        self.decided_by_agent_id = decided_by_agent_id
        self.beneficiary_id = beneficiary_id
        self.cost = estimated_cost
        self.tx_id: Optional[str] = None
        self.aborted = False

    async def __aenter__(self) -> "SafeTwoPhaseCommitContextV10":
        self.tx_id = await self.client.enforce_tool_gate(
            tool_name=self.tool_name,
            arguments=self.arguments,
            intent_goal=self.intent_goal,
            evidence_confirming_hashes=self.evidence_confirming_hashes,
            evidence_contradicting_hashes=self.evidence_contradicting_hashes,
            decided_by_agent_id=self.decided_by_agent_id,
            beneficiary_id=self.beneficiary_id,
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
