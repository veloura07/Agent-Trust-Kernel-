"""CSF cross-language test vectors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sel_v3.csf import build_signing_string, canonicalize_args
from sel_v3.crypto import compute_signature, derive_agent_secret

VECTORS_PATH = Path(__file__).parent / "test_vectors.json"


@pytest.fixture
def vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def test_canonicalize_args(vectors: dict) -> None:
    assert canonicalize_args(vectors["args"]) == vectors["expectedCanonicalArgs"]


def test_build_signing_string(vectors: dict) -> None:
    signing = build_signing_string(
        vectors["nonce"],
        vectors["timestamp"],
        vectors["agentId"],
        vectors["toolName"],
        vectors["args"],
    ).decode("utf-8")
    expected = (
        f"{vectors['nonce']}\n{vectors['timestamp']}\n{vectors['agentId']}\n"
        f"{vectors['toolName']}\n{vectors['expectedCanonicalArgs']}"
    )
    assert signing == expected


def test_cross_language_signature(vectors: dict) -> None:
    from sel_v3.crypto import derive_time_gated_secret

    secret = derive_time_gated_secret(
        vectors["masterSecret"], vectors["agentId"], vectors["epoch"]
    )
    sig = compute_signature(
        secret,
        vectors["nonce"],
        vectors["timestamp"],
        vectors["agentId"],
        vectors["toolName"],
        vectors["args"],
    )
    assert sig == vectors["expectedSignature"]
