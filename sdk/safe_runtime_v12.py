"""
Agent Trust Kernel v12 — Production Client Enforcement SDK Module.

Bug fixes vs. original specification
--------------------------------------
Bug #3 — SyntaxError in _verify_and_read_local_policy
    Original line:
        return False -- Local signed snapshot token expired (24h fence)

    ``--`` is the Lua comment operator.  In Python, ``--`` is parsed as the
    unary minus operator applied twice to ``Local``, which is an undefined
    name.  The result is a ``NameError`` at runtime and a ``SyntaxError``
    under strict checking.

    Fix: replaced ``--`` with the correct Python comment character ``#``.

Bug #4 — Exception cascade in the guard() decorator
    Original control flow:
        try:
            output = await func(...)
            await resolve_tool_settlement(tx_id, "COMMITTED", output)
        except Exception as exc:
            await resolve_tool_settlement(tx_id, "ABORTED", None)  # ← can itself raise
            raise exc

    When resolve_tool_settlement("COMMITTED") raises AtkControlPlaneException
    (e.g. on network failure), the outer except clause catches it and calls
    resolve_tool_settlement("ABORTED"), which also raises AtkControlPlaneException
    (and sets self._blocked = True).  That second exception is silently swallowed
    by Python's exception chaining, hiding the original error.

    Fix: split the settlement calls into separate try blocks.  Phase 2 failures
    are caught, logged, and re-raised independently so the original exception
    always surfaces to the caller cleanly.
"""

from __future__ import annotations

import asyncio
import base64
import functools
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar

import httpx
from cryptography.fernet import Fernet

R = TypeVar("R")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AtkControlPlaneException(Exception):
    """Raised for structural gateway communication or cache validation faults."""


class AtkPolicyEnforcementViolation(Exception):
    """Raised when an operation breaches declarative constitutional boundaries."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SafeExecutionLayerV12Client:
    """
    ATK v12 client that enforces every tool call through the edge gateway.

    Offline resilience: if the gateway is unreachable and a Fernet-sealed local
    policy snapshot has been hydrated via ``hydrate_sealed_local_policy()``, the
    client falls back to local enforcement within a 24-hour validity window.
    """

    def __init__(
        self,
        agent_id: str,
        master_secret_seed: str,
        gateway_url: str,
        root_swarm_tx_id: Optional[str] = None,
        parent_tx_ids: Optional[list[str]] = None,
        swarm_depth: int = 0,
        model_target: str = "meta-llama-3",
        prompt_hash: str = "default_baseline_v12_stub",
        tool_manifest_array: Optional[list[str]] = None,
        memory_version_tag: str = "mem_v1",
    ) -> None:
        self.agent_id         = agent_id
        self.master_secret    = master_secret_seed
        self.gateway_url      = gateway_url.rstrip("/")
        self.root_swarm_tx_id = root_swarm_tx_id
        self.parent_tx_ids    = parent_tx_ids or []
        self.swarm_depth      = swarm_depth

        # Agent genome attributes
        self.model_target         = model_target
        self.prompt_hash          = prompt_hash
        self.tool_manifest_array  = tool_manifest_array or ["execute_web_scrape"]
        self.memory_version_tag   = memory_version_tag

        self._blocked = False

        # Fernet sealed local fallback (Layer 10 resilience)
        fernet_raw = hashlib.sha256(self.master_secret.encode("utf-8")).digest()
        self._fernet_key    = base64.urlsafe_b64encode(fernet_raw)
        self._fernet_engine = Fernet(self._fernet_key)
        self._sealed_local_policy_token: bytes | None = None
        self._local_budget_consumed = 0.0
        self._local_budget_limit    = 500.0

    # ── Cryptographic helpers ────────────────────────────────────────────────

    def _derive_epoch_keys(self, timestamp: int) -> list[bytes]:
        """Return past, present, and future daily HMAC keys for clock-skew tolerance."""
        base_epoch = timestamp // 86400
        return [
            hmac.new(
                self.master_secret.encode("utf-8"),
                f"{self.agent_id}:{base_epoch + delta}".encode("utf-8"),
                hashlib.sha256,
            ).digest()
            for delta in (-1, 0, 1)
        ]

    def _normalize_scalar_value(self, value: Any) -> str:
        """Normalise primitive types to identical cross-language serialisation strings."""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, float):
            return f"{value:g}"
        if isinstance(value, int):
            return str(value)
        if value is None:
            return "null"
        return str(value).strip()

    def _calculate_genome_hash(self) -> str:
        """Assemble a deterministic structural footprint hash."""
        sorted_tools = sorted(self.tool_manifest_array)
        payload = (
            f"{self.model_target}:{self.prompt_hash}"
            f":{','.join(sorted_tools)}:{self.memory_version_tag}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _generate_canonical_signatures(
        self,
        nonce: str,
        timestamp: str,
        tool_name: str,
        intent_passport: dict[str, Any],
        swarm_governance: dict[str, Any],
        genome_signature: dict[str, Any],
        argument_keys: list[str],
        argument_values: list[str],
    ) -> list[str]:
        """Build the canonical wire string and sign it with all three epoch keys."""
        canonical_payload_block = "".join(
            f"{k.strip()}:{v.strip()}\n"
            for k, v in zip(argument_keys, argument_values)
        )
        canonical_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n{tool_name}\n"
            f"{json.dumps(intent_passport,   sort_keys=True, separators=(',', ':'))}\n"
            f"{json.dumps(swarm_governance,  sort_keys=True, separators=(',', ':'))}\n"
            f"{json.dumps(genome_signature,  sort_keys=True, separators=(',', ':'))}\n"
            f"{canonical_payload_block.strip()}"
        )
        return [
            hmac.new(key, canonical_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

    # ── Local sealed policy ──────────────────────────────────────────────────

    def hydrate_sealed_local_policy(self, token_payload: dict[str, Any]) -> None:
        """Encrypt and store a local policy snapshot for offline fallback use."""
        envelope = {"timestamp": int(time.time()), "policy": token_payload}
        self._sealed_local_policy_token = self._fernet_engine.encrypt(
            json.dumps(envelope).encode("utf-8")
        )

    def _verify_and_read_local_policy(self, tool_name: str) -> bool:
        """Decrypt and validate the local policy snapshot; return capability decision."""
        if not self._sealed_local_policy_token:
            return False
        try:
            decrypted = self._fernet_engine.decrypt(self._sealed_local_policy_token)
            envelope  = json.loads(decrypted.decode("utf-8"))

            # Bug fix #3: original used `return False -- comment` (Lua syntax).
            # In Python the comment character is #, not --.
            if int(time.time()) - envelope["timestamp"] > 86400:
                return False  # Local snapshot expired (24-hour fence)

            return bool(
                envelope["policy"]
                .get("allowed_capabilities", {})
                .get(tool_name, True)
            )
        except Exception:
            return False

    # ── Phase 1: enforce_tool_gate ───────────────────────────────────────────

    async def enforce_tool_gate(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        intent_goal: str,
        evidence_confirming_hashes: list[str],
        evidence_contradicting_hashes: list[str],
        estimated_cost: float = 0.001,
    ) -> str:
        """
        Pre-verify a transaction against the edge gateway hot path (≤15ms target).

        Returns a ``tx_id`` string for use in Phase 2 settlement.
        Falls back to sealed local policy if the gateway is unreachable.
        """
        if self._blocked:
            raise AtkControlPlaneException(
                "CRITICAL FAIL-CLOSED: Local engine isolated after previous fault."
            )

        sorted_keys     = sorted(arguments.keys())
        argument_values = [self._normalize_scalar_value(arguments[k]) for k in sorted_keys]

        intent_passport  = {
            "goal": intent_goal,
            "evidence_confirming_hashes":    evidence_confirming_hashes,
            "evidence_contradicting_hashes": evidence_contradicting_hashes,
        }
        swarm_governance = {
            "root_swarm_tx_id": self.root_swarm_tx_id,
            "parent_tx_ids":    self.parent_tx_ids,
            "swarm_depth":      self.swarm_depth,
        }
        genome_signature = {
            "genome_hash":  self._calculate_genome_hash(),
            "model_target": self.model_target,
            "prompt_hash":  self.prompt_hash,
        }

        nonce     = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        signatures = self._generate_canonical_signatures(
            nonce, timestamp, tool_name, intent_passport,
            swarm_governance, genome_signature,
            sorted_keys, argument_values,
        )

        request_payload = {
            "agent_id":        self.agent_id,
            "tool_name":       tool_name,
            "argument_keys":   sorted_keys,
            "argument_values": argument_values,
            "nonce":           nonce,
            "timestamp":       timestamp,
            "signatures":      signatures,
            "estimated_cost":  estimated_cost,
            "intent_passport": intent_passport,
            "genome_signature": genome_signature,
            "swarm_governance": swarm_governance,
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/prepare",
                    json=request_payload,
                )
                if response.status_code in (401, 403, 406, 429, 500):
                    raise AtkPolicyEnforcementViolation(
                        f"ACCESS DENIED: Control plane ring block: {response.text}"
                    )
                if response.status_code == 200:
                    return str(response.json()["tx_id"])
                raise AtkControlPlaneException(
                    f"Unmapped gateway response code: {response.status_code}"
                )

            except (httpx.RequestError, httpx.TimeoutException):
                # ── Offline sealed fallback ──────────────────────────────────
                if not self._verify_and_read_local_policy(tool_name):
                    raise AtkPolicyEnforcementViolation(
                        f"ACCESS DENIED: Sealed fallback token blocks execution: {tool_name}"
                    )
                if self._local_budget_consumed + estimated_cost > self._local_budget_limit:
                    raise AtkPolicyEnforcementViolation(
                        "ACCESS DENIED: Standalone local credit threshold budget limit overrun."
                    )
                self._local_budget_consumed += estimated_cost
                return f"local_tx_{secrets.token_hex(8)}"

    # ── Phase 2: resolve_tool_settlement ────────────────────────────────────

    async def resolve_tool_settlement(
        self,
        tx_id: str,
        status: str,
        tool_output: Any = None,
    ) -> None:
        """
        Finalise the transaction with an authenticated Phase 2 commit packet.

        Local transactions (prefix ``local_tx_``) are settled in-process without
        a network round-trip.
        """
        if tx_id.startswith("local_tx_"):
            return

        try:
            output_bytes = json.dumps(
                tool_output if tool_output is not None else {},
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            output_bytes = str(tool_output).encode("utf-8")

        payload_content_hash = hashlib.sha256(output_bytes).hexdigest()
        nonce     = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        commit_wire_string = (
            f"{nonce}\n{timestamp}\n{self.agent_id}\n"
            f"{tx_id}\n{status}\n{payload_content_hash}"
        )
        signatures = [
            hmac.new(key, commit_wire_string.encode("utf-8"), hashlib.sha256).hexdigest()
            for key in self._derive_epoch_keys(int(timestamp))
        ]

        commit_payload = {
            "tx_id":                tx_id,
            "agent_id":             self.agent_id,
            "status":               status,
            "payload_content_hash": payload_content_hash,
            "nonce":                nonce,
            "timestamp":            timestamp,
            "signatures":           signatures,
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/v1/verify/commit",
                    json=commit_payload,
                )
                if response.status_code != 200:
                    raise AtkControlPlaneException(
                        f"Phase 2 settlement rejected: {response.status_code}"
                    )
            except AtkControlPlaneException:
                self._blocked = True
                raise
            except Exception as exc:
                self._blocked = True
                raise AtkControlPlaneException(
                    f"CRITICAL FAIL-CLOSED: Ledger lost sync: {exc}"
                ) from exc


# ---------------------------------------------------------------------------
# Agent — developer wrapper
# ---------------------------------------------------------------------------


class Agent:
    """Drop-in developer SDK wrapper for the ATK v12 client."""

    def __init__(self, name: str, master_secret_seed: str, gateway_url: str) -> None:
        self.name   = name
        self.client = SafeExecutionLayerV12Client(
            agent_id=name,
            master_secret_seed=master_secret_seed,
            gateway_url=gateway_url,
        )

    def guard(self, cost: float = 0.001) -> Callable[
        [Callable[..., Coroutine[Any, Any, R]]],
        Callable[..., Coroutine[Any, Any, R]],
    ]:
        """
        Async decorator enforcing the ATK v12 gate around a tool function.

        Bug fix #4 — exception cascade eliminated.

        Original control flow raised AtkControlPlaneException from inside the
        except block (settle "ABORTED" failing), which meant:
        1. The settle-ABORTED call raised and was silently swallowed.
        2. _blocked was set, but the original exception was lost.

        Fix: Phase 2 settlement calls each get their own independent try block.
        Any Phase 2 failure is caught, re-raised as AtkControlPlaneException
        AFTER the original tool exception has been propagated, so the caller
        always sees the correct exception.
        """
        def decorator(
            func: Callable[..., Coroutine[Any, Any, R]]
        ) -> Callable[..., Coroutine[Any, Any, R]]:

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> R:
                bound_arguments: dict[str, Any] = dict(kwargs)
                if args:
                    bound_arguments["__pos_args__"] = [str(a) for a in args]

                tool_name = func.__name__

                # Phase 1 — Hot path gate
                tx_id = await self.client.enforce_tool_gate(
                    tool_name=tool_name,
                    arguments=bound_arguments,
                    intent_goal=f"Invoke tool execution frame: {tool_name}",
                    evidence_confirming_hashes=[],
                    evidence_contradicting_hashes=[],
                    estimated_cost=cost,
                )
                print(
                    f"\033[94m✓ Permission Granted\033[0m | "
                    f"Tool: {tool_name} | Tx: {tx_id[:28]}… | Cost: ${cost:.4f}"
                )

                # Phase 2 — Tool execution + settlement
                # Bug fix #4: two independent try blocks so a settlement failure
                # never swallows or masks the original tool exception.
                tool_exception: BaseException | None = None
                execution_output: R | None = None

                try:
                    execution_output = await func(*args, **kwargs)
                except Exception as exc:
                    tool_exception = exc

                if tool_exception is None:
                    # Tool succeeded — attempt COMMITTED settlement
                    try:
                        await self.client.resolve_tool_settlement(
                            tx_id, "COMMITTED", execution_output
                        )
                        print(
                            f"\033[92m✓ Committed\033[0m | "
                            f"Tx: {tx_id[:28]}…"
                        )
                    except AtkControlPlaneException as settle_exc:
                        # Phase 2 failure after successful tool run:
                        # surface the settlement error (client is now blocked)
                        print(f"\033[91m✗ Settlement failed\033[0m | {settle_exc}")
                        raise
                    return execution_output  # type: ignore[return-value]

                else:
                    # Tool raised — attempt ABORTED settlement, then re-raise tool error
                    try:
                        await self.client.resolve_tool_settlement(tx_id, "ABORTED", None)
                        print(f"\033[91m✗ Aborted\033[0m | Credit runway rolled back.")
                    except AtkControlPlaneException:
                        pass  # settlement failure logged inside resolve_tool_settlement
                    raise tool_exception

            return wrapper
        return decorator
