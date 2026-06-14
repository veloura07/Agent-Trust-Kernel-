CREATE SCHEMA IF NOT EXISTS atk_v6;

DROP TRIGGER IF EXISTS trg_v6_agent_registry_updated_at ON atk_v6.agent_registry;
DROP FUNCTION IF EXISTS atk_v6.sync_updated_at();

CREATE TABLE IF NOT EXISTS atk_v6.agent_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    system_version VARCHAR(32) NOT NULL DEFAULT '6.0.0',
    environment VARCHAR(32) NOT NULL DEFAULT 'PRODUCTION',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    velocity_burst_ceiling INT NOT NULL DEFAULT 120,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_daily_budget_positive CHECK (daily_budget_limit >= 0)
);

CREATE TABLE IF NOT EXISTS atk_v6.execution_ledger (
    tx_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v6.agent_registry(agent_id) ON DELETE RESTRICT,
    tool_name VARCHAR(128) NOT NULL,
    transaction_state VARCHAR(32) NOT NULL,
    parent_tx_id UUID NULL REFERENCES atk_v6.execution_ledger(tx_id) ON DELETE RESTRICT,
    intent_passport_hash VARCHAR(64) NOT NULL,
    tool_arguments JSONB NOT NULL,
    payload_content_hash VARCHAR(64) NOT NULL,
    semantic_safety_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    allocated_cost NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    edge_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMPTZ NULL,
    CONSTRAINT chk_transaction_state_valid CHECK (transaction_state IN ('PREPARED', 'COMMITTED', 'ABORTED', 'CLIENT_ABANDONED', 'TIMEOUT'))
);

CREATE TABLE IF NOT EXISTS atk_v6.memory_provenance (
    log_id BIGSERIAL PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v6.agent_registry(agent_id) ON DELETE RESTRICT,
    memory_key VARCHAR(255) NOT NULL,
    historical_context_hash VARCHAR(64) NOT NULL,
    mutation_delta NUMERIC(5, 4) NOT NULL,
    is_quarantined BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_v6_ledger_swarm_trace ON atk_v6.execution_ledger (parent_tx_id, intent_passport_hash);
CREATE INDEX IF NOT EXISTS idx_v6_memory_quarantine ON atk_v6.memory_provenance (agent_id, mutation_delta) WHERE is_quarantined = TRUE;
CREATE INDEX IF NOT EXISTS idx_v6_state_timestamp_lookup ON atk_v6.execution_ledger (transaction_state, edge_timestamp DESC);

CREATE OR REPLACE FUNCTION atk_v6.sync_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v6_agent_registry_updated_at BEFORE UPDATE ON atk_v6.agent_registry FOR EACH ROW EXECUTE FUNCTION atk_v6.sync_updated_at();

ALTER TABLE atk_v6.agent_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v6.execution_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v6.memory_provenance ENABLE ROW LEVEL SECURITY;

CREATE POLICY v6_agent_registry_service_only ON atk_v6.agent_registry FOR ALL USING (false);
CREATE POLICY v6_execution_ledger_service_only ON atk_v6.execution_ledger FOR ALL USING (false);
CREATE POLICY v6_memory_provenance_service_only ON atk_v6.memory_provenance FOR ALL USING (false);

INSERT INTO atk_v6.agent_registry (agent_id, owner_email, system_version, environment, is_active, daily_budget_limit, velocity_burst_ceiling)
VALUES ('autonomous_ops_worker', 'enterprise-dev@company.com', '6.0.0', 'PRODUCTION', true, 500.0000, 120) ON CONFLICT (agent_id) DO NOTHING;
