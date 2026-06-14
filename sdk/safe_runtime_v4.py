"""Agent Trust Kernel v4 — async client with epoch keys, lease heartbeats, output sanitization."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

import httpx


class AtkControlPlaneException(Exception):
    """Raised for structural communication failures or unmapped response states."""


class AtkPolicyEnforcementViolation(Exception):
    """Raised when an action violates authorization boundaries or parameters."""


class SafeExecutionLayerV4Client:
    def __init__(self, agent_id: str, master_secret_seed: str, gateway_url: str):
        self.agent_id = agent_id
        self.master_secret = master_secret_seed
        self.gateway_url = gateway_url.rstrip("/")
        self._blocked = False

    def _derive_current_epoch_key(self, timestamp_seconds: int | None = None) -> bytes:
        current_epoch = int(time.time()) // 86400
        if timestamp_seconds is not None:
            current_epoch = timestamp_seconds // 86400
        payload = f"{self.agent_id}:{current_epoch}"
        return hmac.new(
            self.master_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def _generate_canonical_signature(
        self, nonce: str, timestamp: str, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        sorted_keys = sorted(arguments.keys())
        sorted_dict = {k: arguments[k] for k in sorted_keys}
        minified_json = json.dumps(sorted_dict, separators=(",", ":"))
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n{minified_json}"
        )
        ts = int(timestamp)
        ts_seconds = ts if len(timestamp) < 13 else ts // 1000
        epoch_secret = self._derive_current_epoch_key(ts_seconds)
        return hmac.new(
            epoch_secret, canonical_wire_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    async def enforce_tool_gate(
        self, tool_name: str, arguments: dict[str, Any], estimated_cost: float = 0.001
    ) -> str:
        """Phase 1: Prepare and authorize the transaction request."""
        if self._blocked:
            raise AtkControlPlaneException(
                "CRITICAL FAIL-CLOSED: SDK blocked after prior control plane fault."
            )

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signature = self._generate_canonical_signature(nonce, timestamp, tool_name, arguments)

        payload = {
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "nonce": nonce,
            "timestamp": timestamp,
            "signature": signature,
            "estimated_cost": str(estimated_cost),
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare", json=payload
                )
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Gateway unreachable. Operational loops paused. Ref: {exc}"
                ) from exc

            if response.status_code in (401, 403):
                raise AtkPolicyEnforcementViolation(
                    f"ACCESS DENIED: Boundary match error: {response.text}"
                )
            if response.status_code == 429:
                raise AtkPolicyEnforcementViolation(
                    "ACCESS DENIED: Daily financial balance runway caps exhausted."
                )

            if response.status_code == 202:
                tx_data = response.json()
                tx_id = tx_data["tx_id"]
                while True:
                    await asyncio.sleep(2.0)
                    try:
                        await client.post(f"{self.gateway_url}/v1/tx/{tx_id}/heartbeat")
                        poll_resp = await client.get(f"{self.gateway_url}/v1/tx/{tx_id}")
                        state_data = poll_resp.json()
                        current_state = state_data.get("state")
                        if current_state == "AUTHORIZED":
                            return tx_id
                        if current_state in (
                            "ABORTED",
                            "CLIENT_ABANDONED",
                            "EXPIRED_OR_NOT_FOUND",
                        ):
                            raise AtkPolicyEnforcementViolation(
                                f"ACCESS DENIED: Review rejected or lease timed out. Token: {tx_id}"
                            )
                    except httpx.RequestError as exc:
                        self._blocked = True
                        raise AtkControlPlaneException(
                            "CRITICAL FAIL-CLOSED: Connection dropped during escalation review."
                        ) from exc

            if response.status_code == 200:
                data = response.json()
                return data.get("tx_id") or data.get("transaction_id", "")

            raise AtkControlPlaneException(
                f"Core engine returned unmapped status: {response.status_code}"
            )

    async def resolve_tool_settlement(
        self, tx_id: str, status: str, tool_output: Any = None
    ) -> None:
        """Phase 2: Submit tool results for semantic sanitization or abort."""
        payload = {
            "tx_id": tx_id,
            "agent_id": self.agent_id,
            "status": status,
            "tool_output": tool_output if tool_output is not None else {},
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/commit", json=payload
                )
                if response.status_code == 403:
                    raise AtkPolicyEnforcementViolation(
                        "CRITICAL ESCALATION: INDIRECT_PROMPT_INJECTION detected in tool output."
                    )
                if response.status_code != 200:
                    raise AtkControlPlaneException(
                        f"Phase 2 Commit rejected with status: {response.status_code}"
                    )
            except AtkPolicyEnforcementViolation:
                raise
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Phase 2 synchronization failure: {exc}"
                ) from exc


class SafeTwoPhaseCommitContext:
    """Async context manager enforcing atomic Phase 2 commitments."""

    def __init__(
        self,
        client: SafeExecutionLayerV4Client,
        tool_name: str,
        arguments: dict[str, Any],
        estimated_cost: float = 0.001,
    ):
        self.client = client
        self.tool_name = tool_name
        self.arguments = arguments
        self.cost = estimated_cost
        self.tx_id: str | None = None
        self.aborted = False

    async def __aenter__(self) -> "SafeTwoPhaseCommitContext":
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
