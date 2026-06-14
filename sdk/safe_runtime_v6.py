"""Agent Trust Kernel v6 — Async Client SDK with Structural Key Extraction."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Optional

# pyrefly: ignore [missing-import]
import httpx


class AtkControlPlaneException(Exception):
    """Raised for structural communication errors or gateway connection drops."""


class AtkPolicyEnforcementViolation(Exception):
    """Raised when an operation breaches declarative boundaries or security checks."""


class SafeExecutionLayerV6Client:
    def __init__(
        self, 
        agent_id: str, 
        master_secret_seed: str, 
        gateway_url: str,
        parent_tx_id: Optional[str] = None,
        intent_passport: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.master_secret = master_secret_seed
        self.gateway_url = gateway_url.rstrip("/")
        self.parent_tx_id = parent_tx_id
        self.intent_passport = intent_passport or "ROOT_CONTEXT"
        self._blocked = False

    def _derive_epoch_keys(self, timestamp: int) -> list[bytes]:
        """Generates past, present, and future keys to guarantee zero clock-drift errors."""
        base_epoch = timestamp // 86400
        target_windows = [base_epoch, base_epoch - 1, base_epoch + 1]
        derived_keys = []
        for epoch in target_windows:
            payload = f"{self.agent_id}:{epoch}"
            key = hmac.new(
                self.master_secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            derived_keys.append(key)
        return derived_keys

    def _generate_canonical_signatures(
        self, nonce: str, timestamp: str, tool_name: str, argument_keys: list[str], argument_values: list[str]
    ) -> list[str]:
        """Compiles keys and values into a strict newline scalar layout to prevent cross-language drift."""
        dynamic_args_payload = ""
        for i in range(len(argument_keys)):
            dynamic_args_payload += f"{argument_keys[i]}:{argument_values[i]}\n"
            
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{self.intent_passport}\n{dynamic_args_payload.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    async def enforce_tool_gate(
        self, tool_name: str, arguments: dict[str, Any], estimated_cost: float = 0.001
    ) -> str:
        """Phase 1: Pre-verify transaction requests, shielding operations against parameter evasion."""
        if self._blocked:
            raise AtkControlPlaneException("CRITICAL FAIL-CLOSED: Client execution loop isolated.")

        # Extract and sort argument keys lexicographically to match edge parsing arrays
        sorted_keys = sorted(arguments.keys())
        argument_values = [str(arguments[k]) for k in sorted_keys]

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signatures = self._generate_canonical_signatures(nonce, timestamp, tool_name, sorted_keys, argument_values)

        payload = {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "argument_keys": sorted_keys,
            "argument_values": argument_values,
            "nonce": nonce,
            "timestamp": timestamp,
            "signatures": signatures,
            "estimated_cost": estimated_cost,
            "parent_tx_id": self.parent_tx_id,
            "intent_passport": self.intent_passport
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare", json=payload
                )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Network gateway lost. Halting. Ref: {exc}"
                ) from exc

            if response.status_code in (401, 403, 429, 500):
                raise AtkPolicyEnforcementViolation(
                    f"ACCESS DENIED: Boundary protection ring block: {response.text}"
                )

            if response.status_code == 200:
                return response.json()["tx_id"]

            raise AtkControlPlaneException(f"Core execution engine returned unmapped code: {response.status_code}")

    async def resolve_tool_settlement(
        self, tx_id: str, status: str, tool_output: Any = None
    ) -> None:
        """Phase 2: Finalize metrics using out-of-band content proofs to eliminate heavy string bloat."""
        output_bytes = json.dumps(tool_output if tool_output is not None else {}, separators=(",", ":")).encode("utf-8")
        payload_content_hash = hashlib.sha256(output_bytes).hexdigest()

        # Phase 2 Object Upload: Securely write tool output payload to the Edge Gateway's R2 storage
        if status == "COMMITTED":
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    upload_resp = await client.put(
                        f"{self.gateway_url}/v1/payload/{payload_content_hash}",
                        content=output_bytes,
                        headers={"Content-Type": "application/json"}
                    )
                    if upload_resp.status_code != 200:
                        raise AtkControlPlaneException(
                            f"Failed to upload tool output to edge gateway storage: {upload_resp.status_code} {upload_resp.text}"
                        )
                except Exception as exc:
                    if not isinstance(exc, AtkControlPlaneException):
                        self._blocked = True
                        raise AtkControlPlaneException(
                            f"CRITICAL FAIL-CLOSED: Tool output upload failed: {exc}"
                        ) from exc
                    raise

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
                if response.status_code == 403:
                    raise AtkPolicyEnforcementViolation(
                        "CRITICAL ESCALATION: Semantic output inspection flagged prompt injection indicators."
                    )
                if response.status_code != 200:
                    raise AtkControlPlaneException(
                        f"Phase 2 verification node rejected settlement: {response.status_code}"
                    )
            except AtkPolicyEnforcementViolation:
                raise
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger database connection broken: {exc}"
                ) from exc


class SafeTwoPhaseCommitContextV6:
    def __init__(
        self, 
        client: SafeExecutionLayerV6Client, 
        tool_name: str, 
        arguments: dict[str, Any], 
        estimated_cost: float = 0.001
    ):
        self.client = client
        self.tool_name = tool_name
        self.arguments = arguments
        self.cost = estimated_cost
        self.tx_id: Optional[str] = None
        self.aborted = False

    async def __aenter__(self) -> "SafeTwoPhaseCommitContextV6":
        self.tx_id = await self.client.enforce_tool_gate(
            self.tool_name, self.arguments, self.cost
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
