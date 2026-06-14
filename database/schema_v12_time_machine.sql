-- ============================================================================
-- AGENT TRUST KERNEL (ATK) v12 - TIME MACHINE STATE REPLAYS SCHEMA
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS atk_v12;

-- ----------------------------------------------------------------------------
-- TABLE: TIME MACHINE REPLAYS
-- Stores immutable state snapshots to enable agent execution replays.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS atk_v12.time_machine_replays (
    replay_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(64) NOT NULL REFERENCES atk_v12.entity_registry(agent_id) ON DELETE RESTRICT,
    parent_replay_id UUID REFERENCES atk_v12.time_machine_replays(replay_id) ON DELETE SET NULL,
    step_index INT NOT NULL,
    state_snapshot JSONB NOT NULL,
    execution_context JSONB NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for optimized chronological queries and state reconstructions
CREATE INDEX IF NOT EXISTS idx_v12_replay_agent_step ON atk_v12.time_machine_replays (agent_id, step_index DESC);
CREATE INDEX IF NOT EXISTS idx_v12_replay_parent ON atk_v12.time_machine_replays (parent_replay_id);

-- Enable Row-Level Security (RLS) policies
ALTER TABLE atk_v12.time_machine_replays ENABLE ROW LEVEL SECURITY;

-- Service role access restriction pattern
CREATE POLICY service_only_time_machine ON atk_v12.time_machine_replays FOR ALL USING (false);
