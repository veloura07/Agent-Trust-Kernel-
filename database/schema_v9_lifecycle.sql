-- ============================================================================
-- AGENT TRUST KERNEL (ATK) v9 TRUST & LIFECYCLE PLATFORM SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v9;

-- Clean existing triggers and functions to guarantee clean installations
DROP TRIGGER IF EXISTS trg_v9_entity_registry_updated_at ON atk_v9.entity_registry;
DROP FUNCTION IF EXISTS atk_v9.sync_updated_at();

-- ----------------------------------------------------------------------------
-- TABLE: AUTONOMOUS ENTITY REGISTRY
-- tracks the lifecycle state of each autonomous entity (agent, swarm, vehicle).
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.entity_registry (
    entity_id VARCHAR(64) PRIMARY KEY,
    owner_email VARCHAR(255) NOT NULL,
    current_lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'CREATION',
    system_version VARCHAR(32) NOT NULL DEFAULT '9.0.0',
    environment VARCHAR(32) NOT NULL DEFAULT 'PRODUCTION',
    daily_budget_limit NUMERIC(12, 4) NOT NULL DEFAULT 500.0000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_lifecycle_state CHECK (current_lifecycle_state IN (
        'CREATION', 'TESTED', 'CERTIFIED', 'STRESS_TESTED', 'DEPLOYED', 'SUSPENDED', 'RETIRED', 'ARCHIVED'
    ))
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY CERTIFICATION (ISO / SOC2 Standards Compliance)
-- Records audit standards, stress test scores, and safety clearances.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.entity_certification (
    certification_id UUID PRIMARY KEY,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    certification_standard VARCHAR(64) NOT NULL DEFAULT 'UL-AGENT-SAFE-v1',
    stress_test_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    governance_check_passed BOOLEAN NOT NULL DEFAULT FALSE,
    certified_by VARCHAR(255) NOT NULL DEFAULT 'ATK-AUTOMATED-CERTIFIER',
    certified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stress_score CHECK (stress_test_score >= 0.00 AND stress_test_score <= 100.00)
);

-- ----------------------------------------------------------------------------
-- TABLE: ENTITY GENOME & EVOLUTION (Tracks Prompts, Models, and Tool drift)
-- Captures the exact configuration footprint of an entity's logic over time.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.entity_genome (
    genome_hash VARCHAR(64) PRIMARY KEY,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    model_name VARCHAR(128) NOT NULL,
    prompt_hash VARCHAR(64) NOT NULL,
    registered_tools VARCHAR(128)[] NOT NULL,
    memory_version VARCHAR(64) NOT NULL DEFAULT 'v1.0.0',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: TOOL RISK REGISTRY (LAYER 7)
-- Authority tool mapping configuration metrics calculating structural risk scores.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.tool_risk_registry (
    tool_name VARCHAR(128) PRIMARY KEY,
    risk_score INT NOT NULL DEFAULT 1,
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    requires_twin_simulation BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_tool_risk_bounds CHECK (risk_score >= 1 AND risk_score <= 10)
);

-- ----------------------------------------------------------------------------
-- TABLE: PLANETARY EXECUTION LEDGER
-- Cryptographic transaction ledger tracking lineages, intent passports, and checksum proofs.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.execution_ledger (
    tx_id UUID PRIMARY KEY,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    tool_name VARCHAR(128) NOT NULL REFERENCES atk_v9.tool_risk_registry(tool_name) ON DELETE RESTRICT,
    transaction_state VARCHAR(32) NOT NULL,
    
    -- Swarm Governance Lineage Fields (Layer 9)
    parent_tx_id UUID NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE RESTRICT,
    root_swarm_tx_id UUID NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE RESTRICT,
    swarm_depth INT NOT NULL DEFAULT 0,
    
    -- Intent Verification Fields (Layer 3)
    declared_intent_goal TEXT NOT NULL,
    intent_evidence_hashes VARCHAR(64)[] NOT NULL,
    intent_confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    
    -- Cryptographic Receipt Proof Fields (Layer 10)
    argument_payload_hash VARCHAR(64) NOT NULL,
    payload_content_hash VARCHAR(64) NOT NULL,
    verifiable_receipt_signature_hash VARCHAR(64) NOT NULL,
    
    allocated_cost NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    edge_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at TIMESTAMPTZ NULL,
    CONSTRAINT chk_v9_allocated_cost_positive CHECK (allocated_cost >= 0),
    CONSTRAINT chk_v9_transaction_state_valid CHECK (transaction_state IN ('PREPARED', 'COMMITTED', 'ABORTED', 'CLIENT_ABANDONED', 'TIMEOUT'))
);

-- ----------------------------------------------------------------------------
-- TABLE: CAUSAL ACCOUNTABILITY LEDGER
-- Not just simple logging. Tracks accountability traces (Who approved, benefit, harm).
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.causal_accountability_ledger (
    ledger_id UUID PRIMARY KEY,
    tx_id UUID NOT NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE CASCADE,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    deciding_entity_id VARCHAR(64) NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    approving_human_id VARCHAR(255) NULL,
    delegating_entity_id VARCHAR(64) NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    beneficiary_id VARCHAR(255) NULL,
    estimated_harm_exposure NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    causality_link_description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: ECONOMIC ROI ENGINE
-- Measures exact cost against the estimated financial value created.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.economic_roi_ledger (
    tx_id UUID PRIMARY KEY REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE CASCADE,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    execution_cost NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    estimated_value_created NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    measured_roi_factor NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: COGNITIVE FINGERPRINT (Expanded DNA behavioral indicators)
-- Establishes risk tolerance, exploration, and uncertainty profiles for comparison.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.cognitive_fingerprint (
    entity_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    exploration_tendency NUMERIC(5, 4) NOT NULL DEFAULT 0.5000,
    risk_tolerance NUMERIC(5, 4) NOT NULL DEFAULT 0.3000,
    tool_preference VARCHAR(128)[] NOT NULL,
    delegation_preference NUMERIC(5, 4) NOT NULL DEFAULT 0.5000,
    uncertainty_handling_score NUMERIC(5, 4) NOT NULL DEFAULT 0.8000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: REALITY EVIDENCE & DISAGREEMENT GRAPH (Reality Verification v2)
-- actively seeks disagreements and logs evidence metrics.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.reality_evidence_graph (
    evidence_id UUID PRIMARY KEY,
    tx_id UUID NOT NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    supporting_evidence_hashes VARCHAR(64)[] NOT NULL,
    contradicting_evidence_hashes VARCHAR(64)[] NOT NULL,
    computed_confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    disagreement_score NUMERIC(5, 4) NOT NULL DEFAULT 0.0000,
    resolution_action VARCHAR(64) NOT NULL DEFAULT 'APPROVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: AGENT TRUST METRICS (LAYER 1 & 3)
-- Live "CPU Scheduler" scoring table evaluating multi-dimensional agent reliability.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.agent_trust (
    entity_id VARCHAR(64) PRIMARY KEY REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    trust_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    success_rate NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    human_approval_rate NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    cost_efficiency_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    policy_compliance_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    memory_reliability_score NUMERIC(5, 4) NOT NULL DEFAULT 1.0000,
    total_violations INT NOT NULL DEFAULT 0,
    total_failures INT NOT NULL DEFAULT 0,
    total_timeouts INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_trust_score_bounds CHECK (trust_score >= 0.00 AND trust_score <= 100.00)
);

-- ----------------------------------------------------------------------------
-- TABLE: CONSTITUTION GOVERNANCE ENGINE (LAYER 4)
-- Declarative legal matrices compiled into out-of-process engine evaluation rules.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.constitutional_rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    rule_condition_expression TEXT NOT NULL,
    consequence_action VARCHAR(32) NOT NULL DEFAULT 'BLOCK',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: CRYPTOGRAPHIC MEMORY PROVENANCE DAG (LAYER 5)
-- Maps memory mutations into a strict verifiable Directed Acyclic Graph network structure.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.memory_trust_dag (
    memory_chunk_hash VARCHAR(64) PRIMARY KEY,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    provenance_source_origin VARCHAR(255) NOT NULL,
    parent_memory_hashes VARCHAR(64)[] NULL, 
    memory_payload_summary TEXT NOT NULL,
    is_verified_origin BOOLEAN NOT NULL DEFAULT FALSE,
    chunk_trust_score NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: EXPLAINABILITY LINEAGE GRAPH (LAYER 4)
-- Captures the semantic cause-and-effect pipeline link tracking for audit queries.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.explainability_graph (
    node_id UUID PRIMARY KEY,
    tx_id UUID NOT NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE CASCADE,
    step_sequence INT NOT NULL,
    decision_node_type VARCHAR(64) NOT NULL, -- EVIDENCE, DECISION, MEMORY_REF, CONSTITUTIONAL_CHECK
    node_description TEXT NOT NULL,
    referenced_memory_hash VARCHAR(64) NULL REFERENCES atk_v9.memory_trust_dag(memory_chunk_hash),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: STATE TIME MACHINE SNAPSHOTS (LAYER 4)
-- Records full prompt contexts, memory allocations, and execution outcomes for system replays.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.state_time_machine (
    snapshot_id BIGSERIAL PRIMARY KEY,
    tx_id UUID NOT NULL REFERENCES atk_v9.execution_ledger(tx_id) ON DELETE CASCADE,
    entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    historical_prompts_minified TEXT NOT NULL,
    historical_memory_context_hashes VARCHAR(64)[] NOT NULL,
    recorded_state_dump JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- TABLE: COLLECTIVE LEARNING NETWORK INTERFACES (LAYER 12)
-- Broadcast bulletin log entries sharing real-time service infrastructure anomalies out-of-band.
-- ----------------------------------------------------------------------------
CREATE TABLE atk_v9.collective_learning_bulletins (
    bulletin_id BIGSERIAL PRIMARY KEY,
    reporting_entity_id VARCHAR(64) NOT NULL REFERENCES atk_v9.entity_registry(entity_id) ON DELETE RESTRICT,
    anomalous_target_interface VARCHAR(255) NOT NULL,
    issue_fingerprint_token VARCHAR(64) NOT NULL,
    evaluation_confidence NUMERIC(5, 4) NOT NULL DEFAULT 0.9500,
    is_globally_broadcast BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- PLANETARY SCALE OPERATIONAL ENGINE ANALYTICAL INDEXES
-- ----------------------------------------------------------------------------
CREATE INDEX idx_v9_ledger_swarm_governance ON atk_v9.execution_ledger (parent_tx_id, root_swarm_tx_id, swarm_depth);
CREATE INDEX idx_v9_memory_dag_graph ON atk_v9.memory_trust_dag USING GIN (parent_memory_hashes);
CREATE INDEX idx_v9_ledger_receipt_checksums ON atk_v9.execution_ledger (argument_payload_hash, payload_content_hash);
CREATE INDEX idx_v9_ledger_state_timestamps ON atk_v9.execution_ledger (transaction_state, edge_timestamp DESC);
CREATE INDEX idx_v9_explain_tx ON atk_v9.explainability_graph (tx_id, step_sequence);
CREATE INDEX idx_v9_time_machine_lookup ON atk_v9.state_time_machine (entity_id, captured_at DESC);
CREATE INDEX idx_v9_causal_ledger_search ON atk_v9.causal_accountability_ledger (deciding_entity_id, created_at DESC);
CREATE INDEX idx_v9_economic_roi ON atk_v9.economic_roi_ledger (entity_id, measured_roi_factor DESC);
CREATE INDEX idx_v9_evidence_disagreement ON atk_v9.reality_evidence_graph (tx_id, computed_confidence);

-- ----------------------------------------------------------------------------
-- TRIGGER: SET AUTOMATED UPDATED_AT TIMESTAMP MUTATIONS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION atk_v9.sync_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_v9_entity_registry_updated_at
    BEFORE UPDATE ON atk_v9.entity_registry
    FOR EACH ROW EXECUTE FUNCTION atk_v9.sync_updated_at();

-- ----------------------------------------------------------------------------
-- ENTERPRISE ROW-LEVEL SECURITY (RLS) SERVICE POLICIES
-- ----------------------------------------------------------------------------
ALTER TABLE atk_v9.entity_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.entity_certification ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.entity_genome ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.tool_risk_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.execution_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.causal_accountability_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.economic_roi_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.cognitive_fingerprint ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.reality_evidence_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.agent_trust ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.constitutional_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.memory_trust_dag ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.explainability_graph ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.state_time_machine ENABLE ROW LEVEL SECURITY;
ALTER TABLE atk_v9.collective_learning_bulletins ENABLE ROW LEVEL SECURITY;

CREATE POLICY v9_entity_registry_isolated ON atk_v9.entity_registry FOR ALL USING (false);
CREATE POLICY v9_entity_certification_isolated ON atk_v9.entity_certification FOR ALL USING (false);
CREATE POLICY v9_entity_genome_isolated ON atk_v9.entity_genome FOR ALL USING (false);
CREATE POLICY v9_tool_risk_registry_isolated ON atk_v9.tool_risk_registry FOR ALL USING (false);
CREATE POLICY v9_execution_ledger_isolated ON atk_v9.execution_ledger FOR ALL USING (false);
CREATE POLICY v9_causal_ledger_isolated ON atk_v9.causal_accountability_ledger FOR ALL USING (false);
CREATE POLICY v9_economic_roi_isolated ON atk_v9.economic_roi_ledger FOR ALL USING (false);
CREATE POLICY v9_cognitive_fingerprint_isolated ON atk_v9.cognitive_fingerprint FOR ALL USING (false);
CREATE POLICY v9_reality_evidence_graph_isolated ON atk_v9.reality_evidence_graph FOR ALL USING (false);
CREATE POLICY v9_agent_trust_isolated ON atk_v9.agent_trust FOR ALL USING (false);
CREATE POLICY v9_constitutional_rules_isolated ON atk_v9.constitutional_rules FOR ALL USING (false);
CREATE POLICY v9_memory_trust_dag_isolated ON atk_v9.memory_trust_dag FOR ALL USING (false);
CREATE POLICY v9_explainability_graph_isolated ON atk_v9.explainability_graph FOR ALL USING (false);
CREATE POLICY v9_state_time_machine_isolated ON atk_v9.state_time_machine FOR ALL USING (false);
CREATE POLICY v9_collective_learning_bulletins_isolated ON atk_v9.collective_learning_bulletins FOR ALL USING (false);

-- ----------------------------------------------------------------------------
-- SEED INITIAL BASELINE DEPLOYMENT SECURITY COMPLIANCE PROFILES
-- ----------------------------------------------------------------------------
INSERT INTO atk_v9.entity_registry (entity_id, owner_email, current_lifecycle_state, system_version, environment, daily_budget_limit)
VALUES ('autonomous_ops_worker', 'enterprise-dev@company.com', 'CREATION', '9.0.0', 'PRODUCTION', 500.0000) ON CONFLICT (entity_id) DO NOTHING;

INSERT INTO atk_v9.entity_genome (genome_hash, entity_id, model_name, prompt_hash, registered_tools, memory_version)
VALUES ('initial_genome_hash_for_v9', 'autonomous_ops_worker', 'gpt-5', 'hash_digest_system_instructions_v9_baseline', ARRAY['research', 'analysis', 'database_write', 'financial_transfer'], 'v1.0.0') ON CONFLICT (genome_hash) DO NOTHING;

INSERT INTO atk_v9.agent_trust (entity_id, trust_score, success_rate, human_approval_rate, cost_efficiency_score, policy_compliance_score, memory_reliability_score)
VALUES ('autonomous_ops_worker', 95.00, 0.9800, 1.0000, 0.9500, 1.0000, 0.9600) ON CONFLICT (entity_id) DO NOTHING;

INSERT INTO atk_v9.cognitive_fingerprint (entity_id, exploration_tendency, risk_tolerance, tool_preference, delegation_preference, uncertainty_handling_score)
VALUES ('autonomous_ops_worker', 0.4000, 0.3000, ARRAY['execute_financial_transfer', 'execute_web_scrape', 'modify_database_record'], 0.5000, 0.8000) ON CONFLICT (entity_id) DO NOTHING;

INSERT INTO atk_v9.tool_risk_registry (tool_name, risk_score, requires_approval, requires_twin_simulation) VALUES 
('execute_financial_transfer', 10, true, true),
('execute_web_scrape', 2, false, false),
('modify_database_record', 7, true, true)
ON CONFLICT (tool_name) DO NOTHING;
