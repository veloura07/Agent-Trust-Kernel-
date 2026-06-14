#!/usr/bin/env python3
"""Seed agent policy into Upstash Redis."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / "atk-policy.json"
AGENT_ID = os.environ.get("ATK_AGENT_ID", "autonomous_ops_worker")


def main() -> None:
    redis_url = os.environ.get("UPSTASH_REDIS_REST_URL", "")
    redis_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

    if not redis_url or not redis_token:
        print("Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN", file=sys.stderr)
        sys.exit(1)

    policy = POLICY_FILE.read_text(encoding="utf-8")
    key = f"policy:{AGENT_ID}"
    payload = json.dumps(["SET", key, policy]).encode("utf-8")

    req = urllib.request.Request(
        redis_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {redis_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    print(f"Seeded {key} -> {result}")


if __name__ == "__main__":
    main()
