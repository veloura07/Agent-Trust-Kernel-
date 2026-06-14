-- Agent Trust Kernel v4 Schema Patch
-- Run in Supabase SQL Editor after schema_v3.sql (or standalone for new deployments)

CREATE SCHEMA IF NOT EXISTS atk_v4;

-- Enhanced agent registry with revocation epoch tracking
CREATE TABLE IF NOT EXISTS atk_v4.agent_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    system_version VARCHAR(32) NOT NULL DEFAULT '4.0.0',
    environment VARCHAR(32) DEFAULT 'PRODUCTION',
    is_active BOOLEAN DEFAULT TRUE,
    revocation_epoch INT DEFAULT 0,
    daily_budget_limit NUMERIC(10, 4) DEFAULT 500.0000,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Upgraded multi-phase transaction ledger
CREATE TABLE IF NOT EXISTS atk_v4.execution_ledger (
    tx_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v4.agent_registry(agent_id),
    tool_name VARCHAR(128) NOT NULL,
    transaction_state VARCHAR(32) NOT NULL,
    tool_arguments JSONB NOT NULL,
    tool_output_summary JSONB,
    policy_decision VARCHAR(32) NOT NULL,
    estimated_cost NUMERIC(10, 4) DEFAULT 0.0000,
    nonce_frame VARCHAR(64) NOT NULL,
    cryptographic_epoch INT NOT NULL,
    client_timestamp TIMESTAMPTZ NOT NULL,
    edge_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    execution_receipt_hash VARCHAR(128),
    error_message TEXT,
    settled_at TIMESTAMPTZ
);

-- Invalidation log tracking matrix
CREATE TABLE IF NOT EXISTS atk_v4.revocation_log (
    id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    revoked_epoch INT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_v4_ledger_epoch
    ON atk_v4.execution_ledger (agent_id, cryptographic_epoch);

CREATE INDEX IF NOT EXISTS idx_v4_state_lookup
    ON atk_v4.execution_ledger (transaction_state);

CREATE INDEX IF NOT EXISTS idx_v4_ledger_args_jsonb
    ON atk_v4.execution_ledger USING GIN (tool_arguments);

CREATE INDEX IF NOT EXISTS idx_v4_revocation_agent
    ON atk_v4.revocation_log (agent_id, revoked_epoch DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION atk_v4.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_v4_agent_registry_updated_at ON atk_v4.agent_registry;
CREATE TRIGGER trg_v4_agent_registry_updated_at
    BEFORE UPDATE ON atk_v4.agent_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v4.set_updated_at();

-- Row Level Security
ALTER TABLE atk_v4.agent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v4.execution_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v4.revocation_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY v4_agent_registry_service_only ON atk_v4.agent_registry
    FOR ALL USING (false);

CREATE POLICY v4_execution_ledger_service_only ON atk_v4.execution_ledger
    FOR ALL USING (false);

CREATE POLICY v4_revocation_log_service_only ON atk_v4.revocation_log
    FOR ALL USING (false);

-- Seed baseline agent for verification tests
INSERT INTO atk_v4.agent_registry (
    agent_id, owner_email, system_version, environment, is_active, revocation_epoch
)
VALUES (
    'autonomous_ops_worker', 'enterprise-dev@company.com', '4.0.0', 'PRODUCTION', true, 0
)
ON CONFLICT (agent_id) DO NOTHING;
