-- ============================================================================
-- AGENTGUARD v12 EVENT-SOURCED STORAGE PLANE & PROJECTIONS
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v12;

-- Drop function and triggers if they exist to avoid errors
DROP TRIGGER IF EXISTS trg_v12_entity_registry_updated_at ON atk_v12.entity_registry;
DROP FUNCTION IF EXISTS atk_v12.sync_updated_at();

CREATE TABLE IF NOT EXISTS atk_v12.tenant_registry (
    tenant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS atk_v12.entity_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES atk_v12.tenant_registry(tenant_id) ON DELETE RESTRICT,
    owner_email VARCHAR(255) NOT NULL,
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'CERTIFIED',
    system_version VARCHAR(32) NOT NULL DEFAULT '12.0.0',
    environment VARCHAR(32) NOT NULL DEFAULT 'PRODUCTION',
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_v12_lifecycle CHECK (lifecycle_state IN ('SPAWNED', 'CERTIFIED', 'DEPLOYED', 'SUSPENDED', 'RETIRED'))
);

CREATE TABLE IF NOT EXISTS atk_v12.execution_event_store (
    event_id BIGSERIAL PRIMARY KEY,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0',
    tx_id UUID NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v12.entity_registry(agent_id) ON DELETE RESTRICT,
    event_type VARCHAR(64) NOT NULL, -- PREPARE_REQUESTED, AUTHORIZED, COMMITTED, ABORTED, ALARM
    event_payload JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS atk_v12.causality_dag (
    tx_id UUID PRIMARY KEY,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0',
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v12.entity_registry(agent_id) ON DELETE RESTRICT,
    tool_name VARCHAR(128) NOT NULL,
    parent_tx_ids UUID[] NULL,
    root_swarm_tx_id UUID NULL,
    declared_intent_goal TEXT NOT NULL,
    argument_payload_hash VARCHAR(64) NOT NULL,
    payload_content_hash VARCHAR(64) NOT NULL,
    settled_state VARCHAR(32) NOT NULL DEFAULT 'PREPARED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS atk_v12.vector_reputation (
    agent_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v12.entity_registry(agent_id) ON DELETE RESTRICT,
    safety_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    accuracy_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    cost_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    reliability_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    alignment_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    last_computed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_v12_event_stream_tx ON atk_v12.execution_event_store (tx_id, event_type);
CREATE INDEX IF NOT EXISTS idx_v12_dag_lineage ON atk_v12.causality_dag USING GIN (parent_tx_ids);
CREATE INDEX IF NOT EXISTS idx_v12_idempotency ON atk_v12.execution_event_store (idempotency_key);

CREATE OR REPLACE FUNCTION atk_v12.sync_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v12_entity_registry_updated_at
    BEFORE UPDATE ON atk_v12.entity_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v12.sync_updated_at();

ALTER TABLE atk_v12.tenant_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.entity_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.execution_event_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.causality_dag ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.vector_reputation ENABLE ROW LEVEL SECURITY;

-- Drop policy if exists to make it idempotent
DROP POLICY IF EXISTS service_only_all ON atk_v12.execution_event_store;
CREATE POLICY service_only_all ON atk_v12.execution_event_store FOR ALL USING (false);
