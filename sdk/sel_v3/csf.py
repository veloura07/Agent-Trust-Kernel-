"""Canonical Serialization Format (CSF) — must match gateway/src/crypto/csf.ts byte-for-byte."""

from __future__ import annotations

import json
from typing import Any


def canonicalize_args(args: dict[str, Any]) -> str:
    """Return minified JSON with keys sorted alphabetically."""
    return json.dumps(args, sort_keys=True, separators=(",", ":"))


def build_signing_string(
    nonce: str,
    timestamp: str,
    agent_id: str,
    tool_name: str,
    args: dict[str, Any],
) -> bytes:
    """Build the newline-delimited signing string as UTF-8 bytes."""
    canonical_args = canonicalize_args(args)
    signing = f"{nonce}\n{timestamp}\n{agent_id}\n{tool_name}\n{canonical_args}"
    return signing.encode("utf-8")
