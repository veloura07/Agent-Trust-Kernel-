-- ============================================================================
-- AGENT TRUST KERNEL (ATK) v12 PLANETARY-SCALE OPERATING SYSTEM STORAGE PLANE
-- ============================================================================
-- Bug fix #1: The original script called
--
--   DROP TRIGGER IF EXISTS trg_v12_entity_registry_updated_at
--     ON atk_v12.entity_registry;
--
-- BEFORE the atk_v12.entity_registry table existed.  In PostgreSQL,
-- DROP TRIGGER … ON <table> errors with "relation does not exist" even
-- when IF EXISTS is specified — IF EXISTS only suppresses the
-- "trigger not found" error, not a missing table error.
--
-- Fix: use DROP FUNCTION … CASCADE instead.  Because the trigger
-- calls the function, dropping the function with CASCADE automatically
-- drops any dependent triggers without needing the table to exist first.
-- IF EXISTS on the function suppresses the "not found" error safely.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v12;

-- Safe idempotent cleanup: CASCADE drops dependent triggers automatically
-- (Bug fix #1 — replaces the trigger DROP that required the table to exist)
DROP FUNCTION IF EXISTS atk_v12.sync_updated_at() CASCADE;

-- ----------------------------------------------------------------------------
-- TABLE: TENANT REGISTRY
-- Isolates corporate organizations and data plane environments.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.tenant_registry (
    tenant_id    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY REGISTRY
-- Authoritative global master tracking autonomous accounts and lifecycle states.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.entity_registry (
    agent_id           VARCHAR(64)    PRIMARY KEY,
    tenant_id          UUID           NOT NULL
                           REFERENCES atk_v12.tenant_registry(tenant_id)
                           ON DELETE RESTRICT,
    owner_email        VARCHAR(255)   NOT NULL,
    lifecycle_state    VARCHAR(32)    NOT NULL DEFAULT 'CERTIFIED',
    system_version     VARCHAR(32)    NOT NULL DEFAULT '12.0.0',
    environment        VARCHAR(32)    NOT NULL DEFAULT 'PRODUCTION',
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_v12_lifecycle CHECK (
        lifecycle_state IN ('SPAWNED', 'CERTIFIED', 'DEPLOYED', 'SUSPENDED', 'RETIRED')
    )
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY GENOMES
-- Structural footprint storage for prompt vectors and model specifications.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.entity_genomes (
    genome_hash          VARCHAR(64) PRIMARY KEY,
    agent_id             VARCHAR(64) NOT NULL
                             REFERENCES atk_v12.entity_registry(agent_id)
                             ON DELETE RESTRICT,
    model_target         VARCHAR(128) NOT NULL,
    prompt_hash          VARCHAR(64)  NOT NULL,
    tool_manifest_array  TEXT[]       NOT NULL,
    memory_version_tag   VARCHAR(64)  NOT NULL,
    compiled_at          TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: MULTI-DIMENSIONAL REPUTATION VECTORS
-- Read-optimised projection tracking un-gameable behavioural metrics.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.vector_reputation (
    agent_id                    VARCHAR(64)    PRIMARY KEY
                                    REFERENCES atk_v12.entity_registry(agent_id)
                                    ON DELETE RESTRICT,
    safety_dimension_score      NUMERIC(5, 2)  NOT NULL DEFAULT 100.00,
    accuracy_dimension_score    NUMERIC(5, 2)  NOT NULL DEFAULT 100.00,
    cost_dimension_score        NUMERIC(5, 2)  NOT NULL DEFAULT 100.00,
    reliability_dimension_score NUMERIC(5, 2)  NOT NULL DEFAULT 100.00,
    alignment_dimension_score   NUMERIC(5, 2)  NOT NULL DEFAULT 100.00,
    total_recalculations_count  BIGINT         NOT NULL DEFAULT 0,
    last_computed_at            TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: APPEND-ONLY EXECUTION EVENT LOG (EVENT SOURCING CORE)
-- The authoritative system source of truth capturing all runtime milestones.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.execution_event_store (
    event_id      BIGSERIAL    PRIMARY KEY,
    tx_id         UUID         NOT NULL,
    agent_id      VARCHAR(64)  NOT NULL
                      REFERENCES atk_v12.entity_registry(agent_id)
                      ON DELETE RESTRICT,
    event_type    VARCHAR(64)  NOT NULL,
    event_payload JSONB        NOT NULL,
    recorded_at   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: ASYMMETRIC CAUSALITY LINEAGE DAG
-- Maps transaction dependencies into a multi-parent Directed Acyclic Graph.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.causality_dag (
    tx_id                    UUID           PRIMARY KEY,
    agent_id                 VARCHAR(64)    NOT NULL
                                 REFERENCES atk_v12.entity_registry(agent_id)
                                 ON DELETE RESTRICT,
    tool_name                VARCHAR(128)   NOT NULL,
    parent_tx_ids            UUID[]         NULL,
    root_swarm_tx_id         UUID           NULL,
    declared_intent_goal     TEXT           NOT NULL,
    argument_payload_hash    VARCHAR(64)    NOT NULL,
    payload_content_hash     VARCHAR(64)    NOT NULL,
    estimated_cost           NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    actual_roi_value         NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    settled_state            VARCHAR(32)    NOT NULL DEFAULT 'PREPARED',
    created_at               TIMESTAMPTZ    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: GRAPH EXPLAINABILITY MATRIX
-- Maps cause-and-effect paths from evidence nodes to final decisions.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.explainability_matrix (
    node_id          UUID        PRIMARY KEY,
    tx_id            UUID        NOT NULL
                         REFERENCES atk_v12.causality_dag(tx_id)
                         ON DELETE CASCADE,
    association_type VARCHAR(64) NOT NULL,
    node_description TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: CRYPTOGRAPHIC MEMORY PROVENANCE TREE
-- Tracks origin contexts to safeguard against vector memory poisoning.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.memory_provenance_tree (
    memory_chunk_hash       VARCHAR(64) PRIMARY KEY,
    agent_id                VARCHAR(64) NOT NULL
                                REFERENCES atk_v12.entity_registry(agent_id)
                                ON DELETE RESTRICT,
    provenance_source_origin VARCHAR(255)  NOT NULL,
    parent_memory_hashes    VARCHAR(64)[] NULL,
    memory_payload_summary  TEXT         NOT NULL,
    is_verified_origin      BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- PERFORMANCE-TUNED INDEX STRUCTURES
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_v12_event_stream_tx
    ON atk_v12.execution_event_store (tx_id, event_type);

CREATE INDEX IF NOT EXISTS idx_v12_dag_lineage
    ON atk_v12.causality_dag USING GIN (parent_tx_ids);

CREATE INDEX IF NOT EXISTS idx_v12_event_store_analytics
    ON atk_v12.execution_event_store (agent_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_v12_explain_lookup
    ON atk_v12.explainability_matrix (tx_id);

CREATE INDEX IF NOT EXISTS idx_v12_memory_tree_gin
    ON atk_v12.memory_provenance_tree USING GIN (parent_memory_hashes);

-- ----------------------------------------------------------------------------
-- TRIGGER: DYNAMIC updated_at COLUMN
-- Table exists at this point — safe to CREATE TRIGGER (Bug fix #1 ordering)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION atk_v12.sync_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v12_entity_registry_updated_at
    BEFORE UPDATE ON atk_v12.entity_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v12.sync_updated_at();

-- ----------------------------------------------------------------------------
-- ROW-LEVEL SECURITY — service_role bypasses RLS in Supabase by default;
-- these policies block authenticated / anon roles from direct table access.
-- ----------------------------------------------------------------------------
ALTER TABLE atk_v12.tenant_registry          ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.entity_registry          ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.entity_genomes           ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.vector_reputation        ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.execution_event_store    ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.causality_dag            ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.explainability_matrix    ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v12.memory_provenance_tree   ENABLE ROW LEVEL SECURITY;

-- Drop existing policies before recreating (idempotent re-run safety)
DROP POLICY IF EXISTS service_only_tenant     ON atk_v12.tenant_registry;
DROP POLICY IF EXISTS service_only_registry   ON atk_v12.entity_registry;
DROP POLICY IF EXISTS service_only_genomes    ON atk_v12.entity_genomes;
DROP POLICY IF EXISTS service_only_reputation ON atk_v12.vector_reputation;
DROP POLICY IF EXISTS service_only_events     ON atk_v12.execution_event_store;
DROP POLICY IF EXISTS service_only_dag        ON atk_v12.causality_dag;
DROP POLICY IF EXISTS service_only_explain    ON atk_v12.explainability_matrix;
DROP POLICY IF EXISTS service_only_memory     ON atk_v12.memory_provenance_tree;

CREATE POLICY service_only_tenant     ON atk_v12.tenant_registry          FOR ALL USING (false);
CREATE POLICY service_only_registry   ON atk_v12.entity_registry          FOR ALL USING (false);
CREATE POLICY service_only_genomes    ON atk_v12.entity_genomes           FOR ALL USING (false);
CREATE POLICY service_only_reputation ON atk_v12.vector_reputation        FOR ALL USING (false);
CREATE POLICY service_only_events     ON atk_v12.execution_event_store    FOR ALL USING (false);
CREATE POLICY service_only_dag        ON atk_v12.causality_dag            FOR ALL USING (false);
CREATE POLICY service_only_explain    ON atk_v12.explainability_matrix    FOR ALL USING (false);
CREATE POLICY service_only_memory     ON atk_v12.memory_provenance_tree   FOR ALL USING (false);

-- ----------------------------------------------------------------------------
-- SEED: SYSTEM COMPLIANCE TESTING RUNTIME BASELINE
-- ----------------------------------------------------------------------------
INSERT INTO atk_v12.tenant_registry (tenant_id, company_name)
VALUES ('00000000-0000-0000-0000-000000000000', 'Enterprise Root Workspace')
ON CONFLICT (tenant_id) DO NOTHING;

INSERT INTO atk_v12.entity_registry
    (agent_id, tenant_id, owner_email, lifecycle_state, daily_budget_limit)
VALUES
    ('autonomous_ops_worker',
     '00000000-0000-0000-0000-000000000000',
     'enterprise-dev@company.com',
     'CERTIFIED',
     500.0000)
ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO atk_v12.vector_reputation
    (agent_id, safety_dimension_score, accuracy_dimension_score,
     cost_dimension_score, reliability_dimension_score, alignment_dimension_score)
VALUES
    ('autonomous_ops_worker', 98.50, 99.00, 97.50, 98.00, 99.00)
ON CONFLICT (agent_id) DO NOTHING;
