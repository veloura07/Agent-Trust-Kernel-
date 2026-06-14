"""SEL v3 HTTP client with fail-closed enforcement."""

from __future__ import annotations

import json
import secrets
import time
import uuid
import urllib.error
import urllib.request
from typing import Any

from sel_v3.crypto import compute_signature, derive_agent_secret


class SELBlockedError(Exception):
    """Raised when the SDK enters fail-closed mode after a control plane fault."""


class SELAuthorizationError(Exception):
    """Raised when the edge gateway denies authorization."""


class SELClient:
    """Zero-dependency SEL v3 client implementing 2PC tool execution."""

    TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        gateway_url: str,
        agent_id: str,
        master_secret: str,
    ) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.agent_id = agent_id
        self.master_secret = master_secret
        self._agent_secret = derive_agent_secret(master_secret, agent_id)
        self._blocked = False

    @property
    def is_blocked(self) -> bool:
        return self._blocked

    def _check_blocked(self) -> None:
        if self._blocked:
            raise SELBlockedError(
                "Control plane fault detected. SDK is fail-closed — no further operations permitted."
            )

    def _fail_closed(self, reason: str) -> None:
        self._blocked = True
        raise SELBlockedError(reason)

    def _sign_request(
        self,
        nonce: str,
        timestamp: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> str:
        return compute_signature(
            self._agent_secret,
            nonce,
            timestamp,
            self.agent_id,
            tool_name,
            args,
        )

    def _post(
        self,
        path: str,
        body: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        self._check_blocked()
        url = f"{self.gateway_url}{path}"
        payload = json.dumps(body).encode("utf-8")
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except Exception:
                detail = {"error": str(exc)}
            raise SELAuthorizationError(
                f"Gateway denied request ({exc.code}): {detail}"
            ) from exc
        except Exception as exc:
            self._fail_closed(
                f"CRITICAL FAULT: Control plane unreachable. Isolate system execution. Ref: {exc}"
            )

    def authorize(
        self,
        tool_name: str,
        args: dict[str, Any],
        cost: float = 0.001,
    ) -> str:
        """Phase 1: request authorization and return transaction_id."""
        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signature = self._sign_request(nonce, timestamp, tool_name, args)

        result = self._post(
            "/v1/authorize",
            {
                "phase": "AUTHORIZED",
                "tool_name": tool_name,
                "args": args,
                "cost": cost,
            },
            headers={
                "X-ATK-Agent-Id": self.agent_id,
                "X-ATK-Nonce": nonce,
                "X-ATK-Timestamp": timestamp,
                "X-ATK-Signature": signature,
            },
        )
        return result.get("transaction_id") or result.get("tx_id", "")

    def settle(
        self,
        transaction_id: str,
        phase: str,
        tool_name: str,
        args: dict[str, Any],
        cost: float,
        result: Any = None,
    ) -> dict[str, Any]:
        """Phase 2: commit or abort a previously authorized transaction."""
        nonce = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signature = self._sign_request(nonce, timestamp, tool_name, args)

        return self._post(
            "/v1/settle",
            {
                "phase": phase,
                "tool_name": tool_name,
                "args": args,
                "cost": cost,
                "result": result,
            },
            headers={
                "X-ATK-Agent-Id": self.agent_id,
                "X-ATK-Nonce": nonce,
                "X-ATK-Timestamp": timestamp,
                "X-ATK-Signature": signature,
                "X-ATK-Transaction-Id": transaction_id,
            },
        )

    def guard(
        self,
        tool_name: str,
        args: dict[str, Any],
        cost: float = 0.001,
    ) -> "GuardContext":
        from sel_v3.context import GuardContext

        return GuardContext(self, tool_name, args, cost)
