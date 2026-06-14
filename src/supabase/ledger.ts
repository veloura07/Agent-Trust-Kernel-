import type { Env } from '../types';

const V4_SCHEMA = 'atk_v4';

export interface LedgerRecord {
  tx_id: string;
  agent_id: string;
  tool_name: string;
  transaction_state: string;
  tool_arguments: Record<string, unknown>;
  tool_output_summary?: Record<string, unknown>;
  policy_decision: string;
  estimated_cost: number;
  nonce_frame: string;
  cryptographic_epoch?: number;
  client_timestamp: string;
  execution_receipt_hash?: string;
  error_message?: string;
}

function supabaseHeaders(env: Env, method: 'POST' | 'PATCH'): Record<string, string> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    'Content-Type': 'application/json',
    'Accept-Profile': V4_SCHEMA,
    'Content-Profile': V4_SCHEMA,
  };
  if (method === 'POST') {
    headers.Prefer = 'return=minimal';
  }
  return headers;
}

export async function syncToSupabase(
  env: Env,
  table: string,
  payload: LedgerRecord | LedgerRecord[],
): Promise<void> {
  const url = `${env.SUPABASE_URL}/rest/v1/${table}`;
  await fetch(url, {
    method: 'POST',
    headers: supabaseHeaders(env, 'POST'),
    body: JSON.stringify(payload),
  });
}

export async function updateLedgerState(
  env: Env,
  txId: string,
  fields: Record<string, unknown>,
): Promise<void> {
  const url = `${env.SUPABASE_URL}/rest/v1/execution_ledger?tx_id=eq.${txId}`;
  await fetch(url, {
    method: 'PATCH',
    headers: supabaseHeaders(env, 'PATCH'),
    body: JSON.stringify({
      ...fields,
      settled_at: new Date().toISOString(),
    }),
  });
}

export async function generateReceipt(
  agentKey: CryptoKey,
  txId: string,
  state: string,
  totalCost: number,
): Promise<string> {
  const message = `${txId}\n${state}\n${totalCost}`;
  const sig = await crypto.subtle.sign(
    'HMAC',
    agentKey,
    new TextEncoder().encode(message),
  );
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}
