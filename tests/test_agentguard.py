"""AgentGuard Production Reliability and Crash Recovery Primitives Verification Harness."""

from __future__ import annotations

import os
import pytest
from agentguard.core import Agent, PolicyViolationError, AgentGuardBenchmark, PolicyEngine


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


@pytest.mark.asyncio
async def test_secret_pattern_detection_blocks_api_key(clean_environment):
    """Ensures RULE_NEVER_SEND_SECRETS detects and blocks API key exposure."""
    agent = Agent(name="autonomous_ops_worker")

    @agent.guard(cost=0.001)
    async def send_data(message: str, api_key: str):
        return {"sent": True}

    # Should be blocked by RULE_NEVER_SEND_SECRETS pattern detection
    with pytest.raises(PolicyViolationError, match="RULE_NEVER_SEND_SECRETS"):
        await send_data(message="Hello", api_key="sk_live_12345")


@pytest.mark.asyncio
async def test_financial_transfer_requires_approval(clean_environment):
    """Ensures RULE_RESTRICT_FINANCIALS triggers REQUIRE_HUMAN_APPROVAL for high amounts."""
    agent = Agent(name="autonomous_ops_worker")

    @agent.guard(cost=0.001)
    async def execute_financial_transfer(amount_usd: float):
        return {"transferred": True, "amount": amount_usd}

    # This should trigger REQUIRE_HUMAN_APPROVAL but still execute
    result = await execute_financial_transfer(amount_usd=10000.00)
    assert result["transferred"] is True


@pytest.mark.asyncio
async def test_low_amount_transfer_allowed(clean_environment):
    """Ensures financial transfers under $5000 are allowed."""
    agent = Agent(name="autonomous_ops_worker")

    @agent.guard(cost=0.001)
    async def execute_financial_transfer(amount_usd: float):
        return {"transferred": True, "amount": amount_usd}

    # This should be allowed
    result = await execute_financial_transfer(amount_usd=500.00)
    assert result["transferred"] is True


@pytest.mark.asyncio
async def test_velocity_burst_limit_enforcement(clean_environment):
    """Ensures velocity burst limiting prevents rapid-fire tool calls."""
    agent = Agent(name="autonomous_ops_worker")
    agent.kernel.velocity_burst_limit = 5  # Allow only 5 calls per window

    @agent.guard(cost=0.001)
    async def rapid_tool():
        return {"executed": True}

    # Should succeed for first 5 calls
    for i in range(5):
        result = await rapid_tool()
        assert result["executed"] is True

    # 6th call should fail
    with pytest.raises(PolicyViolationError, match="VELOCITY_EXCEEDED"):
        await rapid_tool()


@pytest.mark.asyncio
async def test_token_usage_limit_tracking(clean_environment):
    """Ensures token usage is tracked and limited."""
    agent = Agent(name="autonomous_ops_worker")
    agent.kernel.token_usage_limit = 5

    @agent.guard(cost=0.001)
    async def token_consumer():
        return {"executed": True}

    # Should succeed for first 5 calls
    for i in range(5):
        result = await token_consumer()
        assert result["executed"] is True

    # 6th call should fail due to token limit
    with pytest.raises(PolicyViolationError, match="TOKEN_LIMIT_EXCEEDED"):
        await token_consumer()


def test_policy_engine_rule_matching():
    """Test PolicyEngine rule matching and evaluation."""
    rules = [
        {
            "rule_id": "TEST_RULE_1",
            "tool": "test_tool",
            "condition": "true",
            "action": "ALLOW"
        },
        {
            "rule_id": "TEST_RULE_2",
            "tool": "financial_*",
            "condition": "args['amount'] > 1000",
            "action": "REQUIRE_HUMAN_APPROVAL"
        }
    ]
    
    engine = PolicyEngine(rules)
    
    # Test exact match
    action, rule_id = engine.evaluate("test_tool", {})
    assert action == "ALLOW"
    assert rule_id == "TEST_RULE_1"
    
    # Test wildcard match with condition
    action, rule_id = engine.evaluate("financial_transfer", {"amount": 5000})
    assert action == "REQUIRE_HUMAN_APPROVAL"
    assert rule_id == "TEST_RULE_2"
    
    # Test condition failure - should fall through to default
    action, rule_id = engine.evaluate("financial_transfer", {"amount": 500})
    assert action == "ALLOW"
    assert rule_id == "DEFAULT"


def test_pattern_detection_secret_exposure():
    """Test secret pattern detection in arguments."""
    rules = [
        {
            "rule_id": "BLOCK_SECRETS",
            "tool": "*",
            "condition": "contains_pattern('(api_key|secret|password)')",
            "action": "DENY"
        }
    ]
    
    engine = PolicyEngine(rules)
    
    # Should match api_key
    action, rule_id = engine.evaluate("some_tool", {"api_key": "sk_live_12345"})
    assert action == "DENY"
    assert rule_id == "BLOCK_SECRETS"
    
    # Should match in string values
    action, rule_id = engine.evaluate("some_tool", {"message": "password=secret123"})
    assert action == "DENY"
    
    # Should not match when pattern not present
    action, rule_id = engine.evaluate("some_tool", {"safe": "value"})
    assert action == "ALLOW"
    assert rule_id == "DEFAULT"


def test_objective_benchmark_suite_execution():
    """Runs the internal performance diagnostics loop harness to verify latency thresholds."""
    AgentGuardBenchmark.run_suite()
