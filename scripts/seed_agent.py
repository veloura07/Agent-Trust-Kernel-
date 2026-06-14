#!/usr/bin/env python3
"""Register or update an agent in Supabase atk_v3.agent_registry."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

AGENT_ID = os.environ.get("ATK_AGENT_ID", "autonomous_ops_worker")
OWNER_EMAIL = os.environ.get("ATK_OWNER_EMAIL", "enterprise-dev@company.com")
DAILY_BUDGET = float(os.environ.get("ATK_DAILY_BUDGET", "500.0"))


def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        sys.exit(1)

    payload = {
        "agent_id": AGENT_ID,
        "owner_email": OWNER_EMAIL,
        "system_version": "3.0.0",
        "environment": "PRODUCTION",
        "is_active": True,
        "daily_budget_limit": DAILY_BUDGET,
    }

    url = f"{supabase_url.rstrip('/')}/rest/v1/agent_registry"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"Agent registered: {AGENT_ID} (HTTP {resp.status})")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        if exc.code == 409 or "duplicate" in detail.lower():
            patch_url = f"{url}?agent_id=eq.{AGENT_ID}"
            patch_req = urllib.request.Request(
                patch_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {service_key}",
                    "apikey": service_key,
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                method="PATCH",
            )
            with urllib.request.urlopen(patch_req) as resp:
                print(f"Agent updated: {AGENT_ID} (HTTP {resp.status})")
        else:
            print(f"Error: {exc.code} {detail}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
