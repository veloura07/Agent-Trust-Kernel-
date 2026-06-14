#!/usr/bin/env python3
"""
ATK Compliance Evaluation Engine.
Evaluates agent tool invocations against policy declarations in atk-policy.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_FILE = ROOT / "atk-policy.json"


class ComplianceEvaluator:
    def __init__(self, policy_path: Path = DEFAULT_POLICY_FILE):
        self.policy_path = policy_path
        self.rules_map = self._load_rules()

    def _load_rules(self) -> dict[str, list[dict[str, Any]]]:
        if not self.policy_path.exists():
            print(f"Warning: Policy file {self.policy_path} not found. Using default rules.", file=sys.stderr)
            return {}
        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            rules_map = {}
            for capability in data.get("capabilities", []):
                tool = capability.get("tool")
                if tool:
                    rules_map[tool] = capability.get("rules", [])
            return rules_map
        except Exception as e:
            print(f"Error parsing policy file: {e}", file=sys.stderr)
            return {}

    def evaluate_invocation(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Evaluates a single tool call against policy rules."""
        rules = self.rules_map.get(tool_name, [])
        violations = []
        verdict = "PASS"

        for rule in rules:
            field = rule.get("field")
            operator = rule.get("operator")
            limit_val = rule.get("value")
            on_violation = rule.get("on_violation", "BLOCK")

            if field not in arguments:
                continue

            actual_val = arguments[field]
            violation_occurred = False

            try:
                # Type alignment for numeric comparison
                if isinstance(limit_val, (int, float)):
                    actual_val = float(actual_val)
                    limit_val = float(limit_val)

                if operator == "GREATER_THAN":
                    violation_occurred = actual_val > limit_val
                elif operator == "LESS_THAN":
                    violation_occurred = actual_val < limit_val
                elif operator == "EQUAL":
                    violation_occurred = actual_val == limit_val
                elif operator == "NOT_EQUAL":
                    violation_occurred = actual_val != limit_val
            except Exception as parse_err:
                violations.append({
                    "field": field,
                    "rule": rule,
                    "error": f"Type mismatch or check error: {parse_err}"
                })
                verdict = "BLOCK"
                continue

            if violation_occurred:
                violations.append({
                    "field": field,
                    "operator": operator,
                    "limit_value": limit_val,
                    "actual_value": actual_val,
                    "on_violation": on_violation
                })
                if on_violation == "BLOCK":
                    verdict = "BLOCK"
                elif on_violation == "ESCALATE" and verdict != "BLOCK":
                    verdict = "ESCALATE"

        return {
            "compliant": verdict == "PASS",
            "verdict": verdict,
            "violations": violations
        }


def main() -> None:
    evaluator = ComplianceEvaluator()

    # Simple compliance tests
    test_cases = [
        {
            "tool": "execute_web_scrape",
            "args": {"url": "https://vault.internal", "depth_limit": 2}
        },
        {
            "tool": "execute_web_scrape",
            "args": {"url": "https://vault.internal", "depth_limit": 4} # Violates (> 3) -> BLOCK
        },
        {
            "tool": "execute_financial_transfer",
            "args": {"amount_usd": 150.0} # Violates (> 100) -> ESCALATE
        }
    ]

    print("=== ATK Constitutional Compliance Evaluation Report ===")
    for idx, case in enumerate(test_cases, 1):
        tool = case["tool"]
        args = case["args"]
        res = evaluator.evaluate_invocation(tool, args)
        print(f"\nTest Case #{idx}: {tool}({args})")
        print(f"  Verdict: {res['verdict']}")
        print(f"  Compliant: {res['compliant']}")
        if res["violations"]:
            print(f"  Violations: {json.dumps(res['violations'], indent=4)}")


if __name__ == "__main__":
    main()
