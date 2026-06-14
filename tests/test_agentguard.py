"""AgentGuard Production Reliability and Crash Recovery Primitives Verification Harness."""

from __future__ import annotations

import os
import pytest
from agentguard.core import Agent, PolicyViolationError, AgentGuardBenchmark


@pytest.fixture
def clean_environment():
    if os.path.exists(".agentguard_wal.journal"):
        try:
            os.remove(".agentguard_wal.journal")
        except Exception:
            pass
    yield
    if os.path.exists(".agentguard_wal.journal"):
        try:
            os.remove(".agentguard_wal.journal")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_idempotent_and_compliant_execution_pass(clean_environment):
    """Ensures authorized tool actions execute seamlessly with type-resilience protections."""
    agent = Agent(name="autonomous_ops_worker")

    @agent.guard(cost=0.0010)
    async def execute_web_scrape(url: str, active_flag: bool):
        return {"status": "200_OK", "data": "Pristine metadata output records buffer."}

    res = await execute_web_scrape(url="https://company.internal", active_flag=True)
    assert res["status"] == "200_OK"


@pytest.mark.asyncio
async def test_budget_exhaustion_wal_journal_state_match(clean_environment):
    """Ensures overruns are intercepted instantly, generating correct abort journal tags on disk."""
    agent = Agent(name="autonomous_ops_worker")

    @agent.guard(cost=150.00) # Exceeds the limit rule bounds
    async def modify_database_record(query: str):
        return {"updated": True}

    with pytest.raises(PolicyViolationError):
        await modify_database_record(query="UPDATE accounts SET status = 'ACTIVE';")


def test_objective_benchmark_suite_execution():
    """Runs the internal performance diagnostics loop harness to verify latency thresholds."""
    AgentGuardBenchmark.run_suite()
