export interface Env {
  ATK_MASTER_ENCRYPTION_SECRET: string;
  UPSTASH_REDIS_REST_URL: string;
  UPSTASH_REDIS_REST_TOKEN: string;
  SUPABASE_URL: string;
  SUPABASE_SERVICE_ROLE_KEY: string;
}

export type TransactionPhase =
  | 'AUTHORIZED'
  | 'COMMITTED'
  | 'ABORTED'
  | 'PENDING'
  | 'CLIENT_ABANDONED';

export type ErrorCode =
  | 'MISSING_HEADERS'
  | 'EXPIRED_TIMESTAMP_WINDOW'
  | 'SIGNATURE_VERIFICATION_FAILED'
  | 'NONCE_REPLAY_DETECTED'
  | 'CAPABILITY_NOT_PERMITTED'
  | 'AGENT_SUSPENDED'
  | 'AGENT_KEY_REVOKED'
  | 'DAILY_BUDGET_EXHAUSTED'
  | 'TRANSACTION_NOT_FOUND'
  | 'TRANSACTION_COMMIT_WINDOW_CLOSED'
  | 'TRANSACTION_NOT_PENDING'
  | 'INVALID_PHASE'
  | 'PROMPT_INJECTION_DETECTED'
  | 'INDIRECT_PROMPT_INJECTION_DETECTED'
  | 'POLICY_VIOLATION_BLOCKED';

export interface RequestBody {
  phase: TransactionPhase;
  tool_name: string;
  args: Record<string, unknown>;
  cost: number;
  result?: unknown;
}

export interface ATKHeaders {
  agentId: string;
  nonce: string;
  timestamp: string;
  signature: string;
  transactionId?: string;
}

export interface PolicyRule {
  field: string;
  operator: 'GREATER_THAN' | 'EQUALS' | 'CONTAINS' | 'LESS_THAN';
  value: unknown;
  on_violation: 'BLOCK' | 'WARN' | 'ESCALATE';
}

export interface PolicyCapability {
  tool: string;
  rules?: PolicyRule[];
}

export interface AgentPolicy {
  capabilities: PolicyCapability[];
}

export interface ValidationContext {
  headers: ATKHeaders;
  body: RequestBody;
  agentSecret: ArrayBuffer;
}

export interface ErrorResponse {
  error: ErrorCode;
  message: string;
}
