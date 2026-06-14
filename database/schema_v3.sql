-- Agent Trust Kernel v3 Database Schema
-- Run in Supabase SQL Editor to initialize the persistent audit ledger.

CREATE SCHEMA IF NOT EXISTS atk_v3;

-- Agent registration matrix
CREATE TABLE IF NOT EXISTS atk_v3.agent_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL DEFAULT 'enterprise-dev@company.com',
    system_version VARCHAR(32) NOT NULL DEFAULT '3.0.0',
    environment VARCHAR(32) DEFAULT 'PRODUCTION',
    is_active BOOLEAN DEFAULT TRUE,
    daily_budget_limit NUMERIC(10, 4) DEFAULT 500.0000,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Immutable transaction and execution ledger
CREATE TABLE IF NOT EXISTS atk_v3.execution_ledger (
    tx_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v3.agent_registry(agent_id),
    tool_name VARCHAR(128) NOT NULL,
    transaction_state VARCHAR(32) NOT NULL,
    tool_arguments JSONB NOT NULL,
    policy_decision VARCHAR(32) NOT NULL,
    estimated_cost NUMERIC(10, 4) DEFAULT 0.0000,
    nonce_frame VARCHAR(64) NOT NULL,
    client_timestamp TIMESTAMPTZ NOT NULL,
    edge_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    execution_receipt_hash VARCHAR(128),
    error_message TEXT,
    settled_at TIMESTAMPTZ
);

-- Append-only memory provenance ledger
CREATE TABLE IF NOT EXISTS atk_v3.memory_provenance (
    log_id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v3.agent_registry(agent_id),
    memory_key VARCHAR(255) NOT NULL,
    context_hash VARCHAR(64) NOT NULL,
    lineage_parent_hash VARCHAR(64),
    operation_type VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- High-performance index optimization
CREATE INDEX IF NOT EXISTS idx_ledger_agent_state
    ON atk_v3.execution_ledger (agent_id, transaction_state);

CREATE INDEX IF NOT EXISTS idx_ledger_args_jsonb
    ON atk_v3.execution_ledger USING GIN (tool_arguments);

CREATE INDEX IF NOT EXISTS idx_memory_key_hash
    ON atk_v3.memory_provenance (agent_id, memory_key);

CREATE INDEX IF NOT EXISTS idx_ledger_edge_timestamp
    ON atk_v3.execution_ledger (edge_timestamp DESC);

-- Auto-update updated_at on agent_registry
CREATE OR REPLACE FUNCTION atk_v3.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_agent_registry_updated_at ON atk_v3.agent_registry;
CREATE TRIGGER trg_agent_registry_updated_at
    BEFORE UPDATE ON atk_v3.agent_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v3.set_updated_at();

-- Row Level Security: service role only
ALTER TABLE atk_v3.agent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v3.execution_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v3.memory_provenance ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_registry_service_only ON atk_v3.agent_registry
    FOR ALL USING (false);

CREATE POLICY execution_ledger_service_only ON atk_v3.execution_ledger
    FOR ALL USING (false);

CREATE POLICY memory_provenance_service_only ON atk_v3.memory_provenance
    FOR ALL USING (false);

-- Seed baseline agent identity for testing
INSERT INTO atk_v3.agent_registry (
    agent_id, owner_email, system_version, environment, is_active, daily_budget_limit
)
VALUES (
    'autonomous_ops_worker', 'enterprise-dev@company.com', '3.0.0', 'PRODUCTION', true, 500.0000
)
ON CONFLICT (agent_id) DO NOTHING;
