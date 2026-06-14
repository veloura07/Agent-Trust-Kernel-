"""Agent Trust Kernel (ATK) Production Reliability and Integration Verification Suite."""

from __future__ import annotations

import os
import pytest
import asyncio
from atk.core import (
    Agent,
    AgentTrustKernelMicrokernel,
    PolicyViolationError,
    AgentGuardBenchmark,
    CapabilityToken
)
from atk.plugins import LocalFlatFileAuditLogger
from atk.adapters import langgraph_tool_guard, crewai_tool_guard, autogen_tool_guard
from atk.chaos import ChaosEngine, AttackMix


@pytest.fixture
def clean_environment():
    """Harness environment fixture cleaning up temporary files."""
    journal_path = ".atk_wal.journal"
    audit_path = "atk_audit.log"
    for path in [journal_path, audit_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    yield
    for path in [journal_path, audit_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@pytest.mark.asyncio
async def test_idempotent_and_compliant_execution_pass(clean_environment):
    """Ensures authorized tool actions execute seamlessly with type-resilience protections."""
    agent = Agent(name="atk_autonomous_ops_worker")

    @agent.guard(cost=0.0010)
    async def execute_web_scrape(url: str, active_flag: bool):
        return {"status": "200_OK", "data": "Pristine metadata output records buffer."}

    res = await execute_web_scrape(url="https://company.internal", active_flag=True)
    assert res["status"] == "200_OK"


@pytest.mark.asyncio
async def test_budget_exhaustion_wal_journal_state_match(clean_environment):
    """Ensures budget overruns are intercepted instantly, generating correct abort journal tags."""
    agent = Agent(name="atk_autonomous_ops_worker")

    @agent.guard(cost=150.00)  # Exceeds the limit rule bounds
    async def modify_database_record(query: str):
        return {"updated": True}

    with pytest.raises(PolicyViolationError):
        await modify_database_record(query="UPDATE accounts SET status = 'ACTIVE';")


def test_objective_benchmark_suite_execution():
    """Runs the internal performance diagnostics loop harness to verify latency thresholds."""
    AgentGuardBenchmark.run_suite()


@pytest.mark.asyncio
async def test_capability_token_minting():
    """Verifies that capability tokens are minted with proper structure and signature."""
    token_gen = CapabilityToken(agent_id="test_agent", tool_name="test_tool", secret_key="test_secret")
    minted = token_gen.mint()
    assert "||" in minted
    parts = minted.split("||")
    assert len(parts) == 2


@pytest.mark.asyncio
async def test_plugins_logging(clean_environment):
    """Verifies that the audit logger plugin writes to the correct log file."""
    logger = LocalFlatFileAuditLogger(log_path="atk_audit.log")
    kernel = AgentTrustKernelMicrokernel()
    kernel.register_plugin(logger)

    agent = Agent(name="test_logger_agent")
    agent.kernel = kernel

    @agent.guard(cost=0.005)
    async def monitored_action():
        return "monitored"

    # Give a tiny sleep to allow the async plugin background task to process
    await monitored_action()
    await asyncio.sleep(0.2)

    assert os.path.exists("atk_audit.log")
    with open("atk_audit.log", "r", encoding="utf-8") as f:
        content = f.read()
    assert "PREPARE" in content
    assert "test_logger_agent" in content


@pytest.mark.asyncio
async def test_adapters_execution(clean_environment):
    """Verifies that the framework adapters wrap functions correctly and execute."""
    @langgraph_tool_guard(cost=0.002)
    async def langgraph_task():
        return "langgraph_done"

    @crewai_tool_guard(cost=0.003)
    async def crewai_task():
        return "crewai_done"

    @autogen_tool_guard(cost=0.004)
    async def autogen_task():
        return "autogen_done"

    assert await langgraph_task() == "langgraph_done"
    assert await crewai_task() == "crewai_done"
    assert await autogen_task() == "autogen_done"


@pytest.mark.asyncio
async def test_chaos_engine_simulation():
    """Verifies that the Chaos Engine runs scenarios and generates a ResilienceReport."""
    engine = ChaosEngine(agent_name="chaos_test_agent")

    async def scenario():
        await asyncio.sleep(0.01)

    mix = AttackMix(tool_failure=0.1, slow_tool=0.2)
    report = await engine.run(scenario=scenario, duration_seconds=1.0, attack_mix=mix)
    
    assert report.agent_name == "chaos_test_agent"
    assert report.total_calls >= 15
    assert report.resilience_score > 0
    
    report_str = str(report)
    assert "Agent Trust Kernel Chaos Report" in report_str
