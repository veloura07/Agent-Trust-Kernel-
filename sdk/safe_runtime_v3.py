"""Agent Trust Kernel v3 — async client enforcement SDK (production blueprint API)."""

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
    """Enforced exception raised for explicit safety locks."""


class AtkPolicyEnforcementViolation(Exception):
    """Enforced when an agent violates policy boundaries."""


def pre_calculate_agent_secret(master_secret: str, agent_id: str) -> str:
    """Derive agent secret locally to match edge HKDF formula."""
    return hmac.new(
        master_secret.encode("utf-8"),
        agent_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class SafeExecutionLayerClient:
    """Async SEL v3 client with fail-closed and human-in-the-loop polling."""

    def __init__(self, agent_id: str, derived_secret_key_hex: str, gateway_url: str):
        self.agent_id = agent_id
        self.secret_bytes = bytes.fromhex(derived_secret_key_hex)
        self.gateway_url = gateway_url.rstrip("/")
        self._blocked = False

    def _generate_canonical_signature(
        self, nonce: str, timestamp: str, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        sorted_keys = sorted(arguments.keys())
        sorted_dict = {k: arguments[k] for k in sorted_keys}
        minified_json = json.dumps(sorted_dict, separators=(",", ":"))
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n{minified_json}"
        )
        return hmac.new(
            self.secret_bytes,
            canonical_wire_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def enforce_tool_gate(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        estimated_cost: float = 0.001,
    ) -> dict[str, Any]:
        if self._blocked:
            raise AtkControlPlaneException(
                "CRITICAL FAULT: SDK is fail-closed after prior control plane fault."
            )

        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signature = self._generate_canonical_signature(
            nonce, timestamp, tool_name, arguments
        )

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
                    f"CRITICAL FAULT: Control plane unreachable. Isolate system execution. Ref: {exc}"
                ) from exc

            if response.status_code in (401, 403):
                raise AtkPolicyEnforcementViolation(
                    f"ACCESS DENIED: Policy restriction blocked execution. Server error payload: {response.text}"
                )
            if response.status_code == 429:
                raise AtkPolicyEnforcementViolation(
                    "ACCESS DENIED: Out of operational runway limits. Daily budget capacity exhausted."
                )

            if response.status_code == 202:
                tx_data = response.json()
                tx_id = tx_data["tx_id"]
                while True:
                    await asyncio.sleep(2.5)
                    try:
                        poll_resp = await client.get(f"{self.gateway_url}/v1/tx/{tx_id}")
                        state_data = poll_resp.json()
                        current_state = state_data.get("state")
                        if current_state == "AUTHORIZED":
                            return {"tx_id": tx_id, "status": "APPROVED"}
                        if current_state in ("ABORTED", "EXPIRED_OR_NOT_FOUND"):
                            raise AtkPolicyEnforcementViolation(
                                f"ACCESS DENIED: Action rejected by manager review workflow tracking token {tx_id}."
                            )
                    except httpx.RequestError as exc:
                        self._blocked = True
                        raise AtkControlPlaneException(
                            "CRITICAL FAULT: Human polling interface lost during live transaction safety holds."
                        ) from exc

            if response.status_code == 200:
                return response.json()

            raise AtkControlPlaneException(
                f"Unhandled explicit gate response frame status sequence: {response.status_code}"
            )


class TwoPhaseCommitContext:
    """Context manager executing Phase-2 commit/abort validation telemetry tracking."""

    def __init__(self, client: SafeExecutionLayerClient, tx_id: str):
        self.client = client
        self.tx_id = tx_id
        self.state = "COMMITTED"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.state = "ABORTED"
