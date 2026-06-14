"""HMAC-SHA256 key derivation and signing — mirrors gateway/src/crypto/csf.ts (v4 epoch keys)."""

from __future__ import annotations

import hmac
import hashlib
import time

from sel_v3.csf import build_signing_string


def get_current_epoch(timestamp_seconds: int | None = None) -> int:
    t = timestamp_seconds if timestamp_seconds is not None else int(time.time())
    return t // 86400


def derive_time_gated_secret(
    master_secret: str, agent_id: str, epoch: int | None = None
) -> bytes:
    """v4: Agent Key = HMAC-SHA256(Master Secret, AgentID:Epoch)."""
    resolved_epoch = epoch if epoch is not None else get_current_epoch()
    payload = f"{agent_id}:{resolved_epoch}"
    return hmac.new(
        master_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()


def derive_agent_secret(master_secret: str, agent_id: str) -> bytes:
    """Derive current-epoch agent secret (v4 default)."""
    return derive_time_gated_secret(master_secret, agent_id)


def compute_signature(
    agent_secret: bytes,
    nonce: str,
    timestamp: str,
    agent_id: str,
    tool_name: str,
    args: dict,
) -> str:
    """Signature = HMAC-SHA256(Agent Secret, Signing String) as hex."""
    signing_string = build_signing_string(
        nonce, timestamp, agent_id, tool_name, args
    )
    return hmac.new(agent_secret, signing_string, hashlib.sha256).hexdigest()
