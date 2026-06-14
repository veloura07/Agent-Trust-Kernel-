"""AgentGuard Open-Source CLI Entrypoint Console Controller Sub-system."""

from __future__ import annotations

import argparse
import os
import sys
from .dashboard import boot_observability_dashboard


def execute_init_sequence() -> None:
    """Generates a pristine declarative configuration file in the target workspace."""
    target_path = "agentguard.yaml"
    if os.path.exists(target_path):
        print(f"\033[93m[!] Configuration blueprint file '{target_path}' already exists in this workspace path.\033[0m")
        return

    yaml_template = """# ============================================================================
# AGENTGUARD DECLARATIVE POLICY-AS-CODE SPECIFICATION
# ============================================================================

workspace:
  tenant_id: "local_dev_workspace_org"
  environment: "DEVELOPMENT"
  multi_tenant_isolation: true

governor:
  daily_budget_ceiling: 25.50
  token_usage_limit: 500000
  execution_timeout_seconds: 10.0
  velocity_burst_limit: 60

compiled_constitution:
  rules:
    - rule_id: "RULE_NEVER_SEND_SECRETS"
      tool: "*"
      condition: "contains_pattern('(?i)(api_key|secret|password|bearer_token)')"
      action: "DENY"
    - rule_id: "RULE_RESTRICT_FINANCIALS"
      tool: "execute_financial_transfer"
      condition: "args['amount_usd'] > 1000.00"
      action: "REQUIRE_HUMAN_APPROVAL"
    - rule_id: "RULE_ALLOW_SCRAPING"
      tool: "execute_web_scrape"
      condition: "true"
      action: "ALLOW"

capability_token_policy:
  default_ttl_seconds: 3600
  cryptographic_signing_algorithm: "HS256"
"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(yaml_template)
    print(f"\033[92m[+] Initialized uncompromised AgentGuard configuration structure inside '{target_path}' successfully.\033[0m")


def main() -> None:
    """Main execution router handling system command allocations."""
    parser = argparse.ArgumentParser(description="AgentGuard Security and Governance CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # agentguard init
    subparsers.add_parser("init", help="Initialize declarative policy configuration files in this workspace.")

    # agentguard inspect --port 8484
    inspect_parser = subparsers.add_parser("inspect", help="Launch the local embedded real-time web observability dashboard console.")
    inspect_parser.add_argument("--port", type=int, default=8484, help="Target network port endpoint to bind web interfaces.")

    args = parser.parse_args()

    if args.command == "init":
        execute_init_sequence()
    elif args.command == "inspect":
        boot_observability_dashboard(port=args.port)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
