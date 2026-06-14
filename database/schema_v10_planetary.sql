-- ============================================================================
-- AGENT TRUST KERNEL (ATK) v10 PLANETARY-SCALE LIFECYCLE OPERATING SYSTEM
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v10;

-- Clean existing trigger and function components to guarantee clean installations
DROP TRIGGER IF EXISTS trg_v10_agent_registry_updated_at ON atk_v10.entity_registry;
DROP FUNCTION IF EXISTS atk_v10.sync_updated_at();

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY REGISTRY
-- Authoritative global master tracking corporate autonomous accounts and lifecycle states.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.entity_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'SPAWNED', -- SPAWNED, CERTIFIED, DEPLOYED, SUSPENDED, RETIRED
    system_version VARCHAR(32) NOT NULL DEFAULT '10.0.0',
    environment VARCHAR(32) NOT NULL DEFAULT 'PRODUCTION',
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_v10_lifecycle_values CHECK (lifecycle_state IN ('SPAWNED', 'CERTIFIED', 'DEPLOYED', 'SUSPENDED', 'RETIRED'))
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY GENOMES
-- Tracks structural prompt, tool configuration signatures, and model matrices.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.entity_genomes (
    genome_hash VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    model_target VARCHAR(128) NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    tool_manifest_array TEXT[] NOT NULL,
    memory_version_tag VARCHAR(64) NOT NULL,
    compiled_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: COGNITIVE FINGERPRINTS
-- Quantifiable behavioral properties measuring execution drift and cognitive profiles.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.cognitive_fingerprints (
    agent_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    exploration_tendency NUMERIC(5, 4) NOT NULL DEFAULT 0.2000,
    risk_tolerance NUMERIC(5, 4) NOT NULL DEFAULT 0.3000,
    tool_preference_index NUMERIC(5, 4) NOT NULL DEFAULT 0.5000,
    delegation_frequency_metric NUMERIC(5, 4) NOT NULL DEFAULT 0.1000,
    uncertainty_handling_score NUMERIC(5, 4) NOT NULL DEFAULT 0.9000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: CERTIFICATION ENGINE
-- Logs stress-test parameters, ISO-standard validation targets, and compliance scores.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.certification_records (
    certification_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    certified_under_version VARCHAR(32) NOT NULL,
    stress_test_score NUMERIC(5, 2) NOT NULL,
    governance_check_passed BOOLEAN NOT NULL DEFAULT FALSE,
    certified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: AGENT PASSPORTS
-- Portable cryptographic identity, skills verification mapping, and violation tallies.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.agent_passports (
    agent_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    owner_organization VARCHAR(255) NOT NULL,
    verified_skills VARCHAR(64)[] NOT NULL,
    total_violations_count INT NOT NULL DEFAULT 0,
    constitution_version VARCHAR(32) NOT NULL DEFAULT '1.4.0',
    synchronized_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: AGENT CONTRACTS
-- SLA Agreement parameters governing accuracy limits, costs, and execution latencies.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.agent_contracts (
    contract_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    target_accuracy_percentage NUMERIC(5, 2) NOT NULL DEFAULT 95.00,
    per_call_cost_limit NUMERIC(10, 4) NOT NULL DEFAULT 1.0000,
    maximum_latency_seconds NUMERIC(6, 3) NOT NULL DEFAULT 5.000,
    current_contract_violations INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: TOOL RISK REGISTRY
-- Authority tool mapping configuration metrics calculating structural interface risk levels.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.tool_risk_registry (
    tool_name VARCHAR(128) PRIMARY KEY,
    risk_score INT NOT NULL DEFAULT 1,
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    requires_twin_simulation BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_v10_tool_risk_bounds CHECK (risk_score >= 1 AND risk_score <= 10)
);

-- ----------------------------------------------------------------------------
-- TABLE: CAUSALITY & ROI LEDGER
-- Deep structural mapping of intent objectives, lineage origins, and value attribution.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.causality_ledger (
    tx_id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    tool_name VARCHAR(128) NOT NULL REFERENCES atk_v10.tool_risk_registry(tool_name) ON DELETE RESTRICT,
    transaction_state VARCHAR(32) NOT NULL,
    
    -- Swarm Lineage Hierarchy
    parent_tx_id UUID NULL REFERENCES atk_v10.causality_ledger(tx_id) ON DELETE RESTRICT,
    root_swarm_tx_id UUID NULL REFERENCES atk_v10.causality_ledger(tx_id) ON DELETE RESTRICT,
    swarm_depth INT NOT NULL DEFAULT 0,
    
    -- Accountability Infrastructure Mapping
    decided_by_agent_id VARCHAR(64) NOT NULL,
    delegated_by_agent_id VARCHAR(64) NULL,
    beneficiary_id VARCHAR(255) NOT NULL,
    harm_profile_json JSONB NOT NULL,
    
    -- Intent Verification & Reality v2 Evidence Graph
    declared_intent_goal TEXT NOT NULL,
    evidence_confirming_hashes VARCHAR(64)[] NOT NULL,
    evidence_contradicting_hashes VARCHAR(64)[] NOT NULL,
    calculated_falsification_index NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    
    -- ROI Economic Attributions
    allocated_cost NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    estimated_economic_value NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    calculated_roi_ratio NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    
    -- Cryptographic Receipt Proof
    argument_payload_hash VARCHAR(64) NOT NULL,
    payload_content_hash VARCHAR(64) NOT NULL,
    verifiable_receipt_signature_hash VARCHAR(64) NOT NULL,
    
    edge_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMPTZ NULL,
    CONSTRAINT chk_v10_transaction_state_valid CHECK (transaction_state IN ('PREPARED', 'COMMITTED', 'ABORTED', 'CLIENT_ABANDONED', 'TIMEOUT'))
);

-- ----------------------------------------------------------------------------
-- TABLE: CRYPTOGRAPHIC MEMORY PROVENANCE DAG
-- Maps memory mutations into a strict verifiable Directed Acyclic Graph network structure.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v10.memory_trust_dag (
    memory_chunk_hash VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v10.entity_registry(agent_id) ON DELETE RESTRICT,
    provenance_source_origin VARCHAR(255) NOT NULL,
    parent_memory_hashes VARCHAR(64)[] NULL, 
    memory_payload_summary TEXT NOT NULL,
    is_verified_origin BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_trust_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- PLANETARY SCALE OPERATIONAL ENGINE ANALYTICAL INDEXES
-- ----------------------------------------------------------------------------
CREATE INDEX idx_v10_ledger_swarm_governance ON atk_v10.causality_ledger (parent_tx_id, root_swarm_tx_id, swarm_depth);
CREATE INDEX idx_v10_memory_dag_graph ON atk_v10.memory_trust_dag USING GIN (parent_memory_hashes);
CREATE INDEX idx_v10_ledger_receipt_checksums ON atk_v10.causality_ledger (argument_payload_hash, payload_content_hash);
CREATE INDEX idx_v10_ledger_state_timestamps ON atk_v10.causality_ledger (transaction_state, edge_timestamp DESC);
CREATE INDEX idx_v10_genomes_lookup ON atk_v10.entity_genomes (agent_id, compiled_at DESC);

-- ----------------------------------------------------------------------------
-- TRIGGER: SET AUTOMATED UPDATED_AT TIMESTAMP MUTATIONS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION atk_v10.sync_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v10_agent_registry_updated_at
    BEFORE UPDATE ON atk_v10.entity_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v10.sync_updated_at();

-- ----------------------------------------------------------------------------
-- ENTERPRISE ROW-LEVEL SECURITY (RLS) SERVICE POLICIES
-- ----------------------------------------------------------------------------
ALTER TABLE atk_v10.entity_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.entity_genomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.cognitive_fingerprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.certification_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.agent_passports ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.agent_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.tool_risk_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.causality_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v10.memory_trust_dag ENABLE ROW LEVEL SECURITY;

CREATE POLICY v10_entity_registry_isolated ON atk_v10.entity_registry FOR ALL USING (false);
CREATE POLICY v10_entity_genomes_isolated ON atk_v10.entity_genomes FOR ALL USING (false);
CREATE POLICY v10_cognitive_fingerprints_isolated ON atk_v10.cognitive_fingerprints FOR ALL USING (false);
CREATE POLICY v10_certification_records_isolated ON atk_v10.certification_records FOR ALL USING (false);
CREATE POLICY v10_agent_passports_isolated ON atk_v10.agent_passports FOR ALL USING (false);
CREATE POLICY v10_agent_contracts_isolated ON atk_v10.agent_contracts FOR ALL USING (false);
CREATE POLICY v10_tool_risk_registry_isolated ON atk_v10.tool_risk_registry FOR ALL USING (false);
CREATE POLICY v10_causality_ledger_isolated ON atk_v10.causality_ledger FOR ALL USING (false);
CREATE POLICY v10_memory_trust_dag_isolated ON atk_v10.memory_trust_dag FOR ALL USING (false);

-- ----------------------------------------------------------------------------
-- SEED SECURITY CONTEXT COMPLIANCE PROFILES
-- ----------------------------------------------------------------------------
INSERT INTO atk_v10.entity_registry (agent_id, owner_email, lifecycle_state, system_version, environment, daily_budget_limit)
VALUES ('autonomous_ops_worker', 'enterprise-dev@company.com', 'CERTIFIED', '10.0.0', 'PRODUCTION', 500.0000) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO atk_v10.agent_passports (agent_id, owner_organization, verified_skills, total_violations_count, constitution_version)
VALUES ('autonomous_ops_worker', 'Enterprise Corp Planetary Infrastructure Workspace Namespace', ARRAY['database_write', 'financial_transfer'], 0, '1.4.0') ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO atk_v10.cognitive_fingerprints (agent_id, exploration_tendency, risk_tolerance, tool_preference_index, delegation_frequency_metric, uncertainty_handling_score)
VALUES ('autonomous_ops_worker', 0.2000, 0.3000, 0.5000, 0.1000, 0.9000) ON CONFLICT (agent_id) DO NOTHING;

INSERT INTO atk_v10.tool_risk_registry (tool_name, risk_score, requires_approval, requires_twin_simulation) VALUES 
('execute_financial_transfer', 10, true, true),
('execute_web_scrape', 2, false, false),
('modify_database_record', 7, true, true)
ON CONFLICT (tool_name) DO NOTHING;
