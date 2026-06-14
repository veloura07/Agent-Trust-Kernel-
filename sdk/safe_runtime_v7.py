"""Agent Trust Kernel v7 — Async Client SDK with Type Normalization Strategy."""

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


class AtkControlPlaneException(RuntimeError):
    """Raised for structural communication errors or gateway connection drops."""


class AtkPolicyEnforcementViolation(RuntimeError):
    """Raised when an operation breaches declarative boundaries or security checks."""


class SafeExecutionLayerV7Client:
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
            return str(value).lower()  # True -> "true", False -> "false"
        if isinstance(value, (int, float)):
            # Trim trailing zero float points to align perfectly with V8 JSON strings
            return f"{value:g}" if isinstance(value, float) else str(value)
        if value is None:
            return "null"
        return str(value).strip()

    def _generate_canonical_signatures(
        self, nonce: str, timestamp: str, tool_name: str, argument_keys: list[str], argument_values: list[str]
    ) -> list[str]:
        """Assembles a stable canonical newline string array to verify transaction signatures."""
        canonical_payload_block = "".join(
            f"{k.strip()}:{v.strip()}\n" for k, v in zip(argument_keys, argument_values)
        )
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{self.intent_passport}\n{canonical_payload_block.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    async def enforce_tool_gate(
        self, tool_name: str, arguments: dict[str, Any], estimated_cost: float = 0.001
    ) -> str:
        """Phase 1: Pre-verify transaction requests, enforcing strict scalar data parsing checks."""
        if self._blocked:
            raise AtkControlPlaneException("CRITICAL FAIL-CLOSED: Local execution loop isolated after previous fault.")

        # Alphabetically sort and cast arguments to eliminate serialization drift exceptions
        sorted_keys = sorted(arguments.keys())
        argument_values = [self._normalize_scalar_value(arguments[k]) for k in sorted_keys]

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
                    f"CRITICAL FAIL-CLOSED: Network control plane dropped connection. Ref: {exc}"
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
                        f"Phase 2 verification node rejected settlement: {response.status_code}"
                    )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger database synchronization dropped: {exc}"
                ) from exc


class SafeTwoPhaseCommitContextV7:
    """Async context manager enforcing atomic Phase 2 commitments."""

    def __init__(
        self, 
        client: SafeExecutionLayerV7Client, 
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

    async def __aenter__(self) -> "SafeTwoPhaseCommitContextV7":
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
