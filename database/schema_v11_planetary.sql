-- ============================================================================
-- AGENT TRUST KERNEL (ATK) v11 DECOUPLED PLANETARY LIFE-CYCLE OS SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v11;

-- Clean existing triggers and function entities to guarantee pristine setups
DROP TRIGGER IF EXISTS trg_v11_entity_registry_updated_at ON atk_v11.entity_registry;
DROP FUNCTION IF EXISTS atk_v11.sync_updated_at();

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY REGISTRY
-- Master state directory managing global autonomous account records.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.entity_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'CERTIFIED', -- SPAWNED, CERTIFIED, DEPLOYED, SUSPENDED, RETIRED
    system_version VARCHAR(32) NOT NULL DEFAULT '11.0.0',
    environment VARCHAR(32) NOT NULL DEFAULT 'PRODUCTION',
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_v11_lifecycle CHECK (lifecycle_state IN ('SPAWNED', 'CERTIFIED', 'DEPLOYED', 'SUSPENDED', 'RETIRED'))
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY GENOMES
-- Structural footprint storage mapping active prompt vectors and model specifications.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.entity_genomes (
    genome_hash VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v11.entity_registry(agent_id) ON DELETE RESTRICT,
    model_target VARCHAR(128) NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    tool_manifest_array TEXT[] NOT NULL,
    memory_version_tag VARCHAR(64) NOT NULL,
    compiled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: MULTI-DIMENSIONAL TRUST PROJECTIONS
-- Materialized read-optimized table tracking agent scores recalculated via Cold Path.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.entity_trust_scores (
    agent_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v11.entity_registry(agent_id) ON DELETE RESTRICT,
    composite_trust_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    safety_rating NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    reliability_rating NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    cost_efficiency_rating NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    accuracy_rating NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    total_recalculations_count BIGINT NOT NULL DEFAULT 0,
    last_computed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: APPEND-ONLY EXECUTION EVENT LOG (EVENT SOURCING CORE)
-- The single source of truth. Captures all transaction state updates as distinct events.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.execution_event_store (
    event_id BIGSERIAL PRIMARY KEY,
    tx_id UUID NOT NULL,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v11.entity_registry(agent_id) ON DELETE RESTRICT,
    event_type VARCHAR(64) NOT NULL, -- PREPARE_REQUESTED, AUTHORIZED, COMMITTED, ABORTED, DEVIATION_ALARM
    event_payload JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: ASYMMETRIC CAUSALITY LINEAGE DAG
-- Maps transaction links recursively into a Directed Acyclic Graph structure.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.causality_dag (
    tx_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v11.entity_registry(agent_id) ON DELETE RESTRICT,
    tool_name VARCHAR(128) NOT NULL,
    parent_tx_ids UUID[] NULL, -- Multi-parent trace linkages tracking mesh networks
    root_swarm_tx_id UUID NULL,
    declared_intent_goal TEXT NOT NULL,
    argument_payload_hash VARCHAR(64) NOT NULL,
    payload_content_hash VARCHAR(64) NOT NULL,
    estimated_cost NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    actual_roi_value NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    settled_state VARCHAR(32) NOT NULL DEFAULT 'PREPARED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: GRAPH EXPLAINABILITY MATRIX
-- Connects actions, decisions, policies, and evidence into an auditable tree layout.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v11.explainability_matrix (
    node_id UUID PRIMARY KEY,
    tx_id UUID NOT NULL REFERENCES atk_v11.causality_dag(tx_id) ON DELETE CASCADE,
    association_type VARCHAR(64) NOT NULL, -- DECISION, EVIDENCE_REF, CONSTITUTIONAL_CHECK
    node_description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- PERFORMANCE TUNED OPERATIONAL SYSTEM INDEXES
-- ----------------------------------------------------------------------------
CREATE INDEX idx_v11_event_stream_tx ON atk_v11.execution_event_store (tx_id, event_type);
CREATE INDEX idx_v11_dag_lineage ON atk_v11.causality_dag USING GIN (parent_tx_ids);
CREATE INDEX idx_v11_event_store_analytics ON atk_v11.execution_event_store (agent_id, recorded_at DESC);
CREATE INDEX idx_v11_explain_lookup ON atk_v11.explainability_matrix (tx_id);

-- ----------------------------------------------------------------------------
-- TRIGGER CONFIGURATION: SET DYNAMIC UPDATED_AT COLUMNS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION atk_v11.sync_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v11_entity_registry_updated_at
    BEFORE UPDATE ON atk_v11.entity_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v11.sync_updated_at();

-- ----------------------------------------------------------------------------
-- SECURED SERVICE BOUNDARY ROW-LEVEL SECURITY (RLS) POLICIES
-- ----------------------------------------------------------------------------
ALTER TABLE atk_v11.entity_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v11.entity_genomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v11.entity_trust_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v11.execution_event_store ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v11.causality_dag ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v11.explainability_matrix ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_only_registry ON atk_v11.entity_registry FOR ALL USING (false);
CREATE POLICY service_only_genomes ON atk_v11.entity_genomes FOR ALL USING (false);
CREATE POLICY service_only_trust ON atk_v11.entity_trust_scores FOR ALL USING (false);
CREATE POLICY service_only_events ON atk_v11.execution_event_store FOR ALL USING (false);
CREATE POLICY service_only_dag ON atk_v11.causality_dag FOR ALL USING (false);
CREATE POLICY service_only_explain ON atk_v11.explainability_matrix FOR ALL USING (false);

-- ----------------------------------------------------------------------------
-- SEED INITIAL SYSTEM SECURITY COMPLIANCE TESTING RUNTIMES
-- ----------------------------------------------------------------------------
INSERT INTO atk_v11.entity_registry (agent_id, owner_email, lifecycle_state, daily_budget_limit)
VALUES ('autonomous_ops_worker', 'enterprise-dev@company.com', 'CERTIFIED', 500.0000) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO atk_v11.entity_trust_scores (agent_id, composite_trust_score, safety_rating, reliability_rating, cost_efficiency_rating, accuracy_rating)
VALUES ('autonomous_ops_worker', 98.50, 99.00, 98.00, 97.50, 99.00) ON CONFLICT (agent_id) DO NOTHING;
