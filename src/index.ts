import { Hono } from 'hono';
import type { Env } from './types';
import { extractHeaders, jsonError, parseBody } from './rings/headers';
import { deriveAgentCryptoKey, getCurrentEpoch } from './rings/derive';
import { deriveTimeGatedSecret } from './crypto/csf';
import { ring3CheckNonce, ring3CheckNonceLegacy } from './rings/nonce';
import {
  detectPromptInjection,
  ring4CheckTimestamp,
  ring4VerifySignature,
  ring4VerifySignatureWithKey,
} from './rings/signature';
import { detectIndirectPromptInjection } from './rings/output-guard';
import { ring5BudgetAndPolicy } from './rings/budget-policy';
import { createRedisClient } from './redis/client';
import { reserveBudget, rollbackBudget } from './redis/budget';
import {
  generateReceipt,
  syncToSupabase,
  updateLedgerState,
} from './supabase/ledger';
import {
  abandonPendingTransaction,
  checkLeaseAbandoned,
  initializePendingLease,
  markAuthorized,
  renewLease,
  revocationKey,
  txKey,
} from './v4/lease';

type AppEnv = { Bindings: Env };

const app = new Hono<AppEnv>();
const DAILY_BUDGET_LIMIT = 500.0;

app.get('/health', (c) => c.json({ status: 'ok', version: '4.0.0' }));

function clientTimestampIso(timestamp: string): string {
  const n = parseInt(timestamp, 10);
  const ms = timestamp.length >= 13 ? n : n * 1000;
  return new Date(ms).toISOString();
}

async function storeTxMeta(
  redis: ReturnType<typeof createRedisClient>,
  txId: string,
  agentId: string,
  cost: number,
): Promise<void> {
  await redis.set(`txmeta:${txId}`, JSON.stringify({ agent_id: agentId, cost }), 3600);
}

async function loadTxMeta(
  redis: ReturnType<typeof createRedisClient>,
  txId: string,
): Promise<{ agent_id: string; cost: number } | null> {
  const raw = await redis.get(`txmeta:${txId}`);
  if (!raw) return null;
  return JSON.parse(raw) as { agent_id: string; cost: number };
}

/** Phase 1: Prepare/Authorize (body-based, v4 epoch keys) */
app.post('/v1/verify/prepare', async (c) => {
  const body = await c.req.json<{
    agent_id?: string;
    tool_name?: string;
    arguments?: Record<string, unknown>;
    nonce?: string;
    timestamp?: string;
    signature?: string;
    estimated_cost?: string | number;
  }>();

  const {
    agent_id,
    tool_name,
    arguments: toolArgs = {},
    nonce,
    timestamp,
    signature,
    estimated_cost = '0.0',
  } = body;

  if (!agent_id || !tool_name || !nonce || !timestamp || !signature) {
    return jsonError('MISSING_HEADERS', 'Mandatory validation attributes are missing', 401);
  }

  const tsError = ring4CheckTimestamp(timestamp);
  if (tsError) return tsError;

  const clientTime = parseInt(timestamp, 10);
  const currentEpoch = getCurrentEpoch(
    timestamp.length >= 13 ? Math.floor(clientTime / 1000) : clientTime,
  );

  const redis = createRedisClient(c.env);

  const revoked = await redis.get(revocationKey(agent_id, currentEpoch));
  if (revoked) {
    return jsonError(
      'AGENT_KEY_REVOKED',
      'Daily key slice has been blacklisted for security containment',
      401,
    );
  }

  const nonceError = await ring3CheckNonceLegacy(redis, nonce);
  if (nonceError) return nonceError;

  const agentKey = await deriveAgentCryptoKey(
    c.env.ATK_MASTER_ENCRYPTION_SECRET,
    agent_id,
    currentEpoch,
  );
  const sigError = await ring4VerifySignatureWithKey(
    agentKey,
    nonce,
    timestamp,
    agent_id,
    tool_name,
    toolArgs,
    signature,
  );
  if (sigError) return sigError;

  const injectionError = detectPromptInjection(toolArgs);
  if (injectionError) return injectionError;

  const costValue = parseFloat(String(estimated_cost));
  const ring5 = await ring5BudgetAndPolicy(
    redis,
    agent_id,
    tool_name,
    toolArgs,
    costValue,
    DAILY_BUDGET_LIMIT,
  );

  if ('error' in ring5) {
    return ring5.error;
  }

  const tx_id = crypto.randomUUID();

  if (ring5.policyResult.escalate) {
    await initializePendingLease(redis, tx_id);
    await storeTxMeta(redis, tx_id, agent_id, costValue);

    c.executionCtx.waitUntil(
      syncToSupabase(c.env, 'execution_ledger', {
        tx_id,
        agent_id,
        tool_name,
        transaction_state: 'PENDING',
        tool_arguments: toolArgs,
        policy_decision: 'ESCALATE',
        estimated_cost: costValue,
        nonce_frame: nonce,
        cryptographic_epoch: currentEpoch,
        client_timestamp: clientTimestampIso(timestamp),
      }),
    );

    return c.json({ status: 'PENDING_APPROVAL', tx_id }, 202);
  }

  await markAuthorized(redis, tx_id);

  const receipt = await generateReceipt(agentKey, tx_id, 'AUTHORIZED', costValue);

  c.executionCtx.waitUntil(
    syncToSupabase(c.env, 'execution_ledger', {
      tx_id,
      agent_id,
      tool_name,
      transaction_state: 'AUTHORIZED',
      tool_arguments: toolArgs,
      policy_decision: 'ALLOW',
      estimated_cost: costValue,
      nonce_frame: nonce,
      cryptographic_epoch: currentEpoch,
      client_timestamp: clientTimestampIso(timestamp),
      execution_receipt_hash: receipt,
    }),
  );

  return c.json({ status: 'AUTHORIZED', tx_id, receipt }, 200);
});

/** Header-based Phase 1 authorization (v4 epoch keys) */
app.post('/v1/authorize', async (c) => {
  const headers = extractHeaders(c.req.raw);
  if (headers instanceof Response) return headers;

  const body = await parseBody(c.req.raw);
  if (body instanceof Response) return body;

  if (body.phase !== 'AUTHORIZED') {
    return jsonError('INVALID_PHASE', 'Authorize endpoint requires phase AUTHORIZED', 400);
  }

  const tsError = ring4CheckTimestamp(headers.timestamp);
  if (tsError) return tsError;

  const clientTime = parseInt(headers.timestamp, 10);
  const currentEpoch = getCurrentEpoch(
    headers.timestamp.length >= 13 ? Math.floor(clientTime / 1000) : clientTime,
  );

  const redis = createRedisClient(c.env);

  const revoked = await redis.get(revocationKey(headers.agentId, currentEpoch));
  if (revoked) {
    return jsonError('AGENT_KEY_REVOKED', 'Daily key slice has been revoked', 401);
  }

  const nonceError = await ring3CheckNonce(redis, headers.agentId, headers.nonce);
  if (nonceError) return nonceError;

  const agentKey = await deriveAgentCryptoKey(
    c.env.ATK_MASTER_ENCRYPTION_SECRET,
    headers.agentId,
    currentEpoch,
  );
  const agentSecretBuffer = await deriveTimeGatedSecret(
    c.env.ATK_MASTER_ENCRYPTION_SECRET,
    headers.agentId,
    currentEpoch,
  );

  const sigError = await ring4VerifySignature(
    agentSecretBuffer,
    headers.nonce,
    headers.timestamp,
    headers.agentId,
    body.tool_name,
    body.args,
    headers.signature,
  );
  if (sigError) return sigError;

  const injectionError = detectPromptInjection(body.args);
  if (injectionError) return injectionError;

  const ring5 = await ring5BudgetAndPolicy(
    redis,
    headers.agentId,
    body.tool_name,
    body.args,
    body.cost,
    DAILY_BUDGET_LIMIT,
  );

  if ('error' in ring5) {
    return ring5.error;
  }

  const tx_id = crypto.randomUUID();

  if (ring5.policyResult.escalate) {
    await initializePendingLease(redis, tx_id);
    await storeTxMeta(redis, tx_id, headers.agentId, body.cost);
    return c.json({ status: 'PENDING_APPROVAL', transaction_id: tx_id }, 202);
  }

  await markAuthorized(redis, tx_id);
  const receipt = await generateReceipt(agentKey, tx_id, 'AUTHORIZED', body.cost);

  c.executionCtx.waitUntil(
    syncToSupabase(c.env, 'execution_ledger', {
      tx_id,
      agent_id: headers.agentId,
      tool_name: body.tool_name,
      transaction_state: 'AUTHORIZED',
      tool_arguments: body.args,
      policy_decision: 'ALLOW',
      estimated_cost: body.cost,
      nonce_frame: headers.nonce,
      cryptographic_epoch: currentEpoch,
      client_timestamp: clientTimestampIso(headers.timestamp),
      execution_receipt_hash: receipt,
    }),
  );

  return c.json({ status: 'AUTHORIZED', transaction_id: tx_id, receipt }, 200);
});

/** Phase 2: Semantic output verification interceptor (v4) */
app.post('/v1/verify/commit', async (c) => {
  const body = await c.req.json<{
    tx_id?: string;
    agent_id?: string;
    status?: string;
    tool_output?: unknown;
  }>();

  const { tx_id, agent_id, status, tool_output } = body;
  if (!tx_id || !agent_id || !status) {
    return jsonError('MISSING_HEADERS', 'tx_id, agent_id, and status are required', 401);
  }

  const redis = createRedisClient(c.env);
  const currentState = await redis.get(txKey(tx_id));

  if (!currentState || currentState !== 'AUTHORIZED') {
    return jsonError(
      'TRANSACTION_COMMIT_WINDOW_CLOSED',
      'Phase 2 confirmation attempted on missing or expired transaction',
      400,
    );
  }

  if (status === 'ABORTED') {
    const meta = await loadTxMeta(redis, tx_id);
    if (meta) {
      await rollbackBudget(redis, meta.agent_id, meta.cost, true);
    }
    await redis.del(txKey(tx_id), `txmeta:${tx_id}`);
    c.executionCtx.waitUntil(
      updateLedgerState(c.env, tx_id, {
        transaction_state: 'ABORTED',
        error_message: 'Client manually aborted execution container thread',
      }),
    );
    return c.json({ status: 'ABORT_ACKNOWLEDGED' });
  }

  const outputError = detectIndirectPromptInjection(tool_output);
  if (outputError) {
    const meta = await loadTxMeta(redis, tx_id);
    if (meta) {
      await rollbackBudget(redis, meta.agent_id, meta.cost, true);
    }
    await redis.del(txKey(tx_id), `txmeta:${tx_id}`);
    c.executionCtx.waitUntil(
      updateLedgerState(c.env, tx_id, {
        transaction_state: 'ABORTED',
        error_message: 'INDIRECT_PROMPT_INJECTION_DETECTED in tool output payload',
      }),
    );
    return outputError;
  }

  const outputString = JSON.stringify(tool_output ?? {});
  await redis.del(txKey(tx_id), `txmeta:${tx_id}`);

  c.executionCtx.waitUntil(
    updateLedgerState(c.env, tx_id, {
      transaction_state: 'COMMITTED',
      tool_output_summary: {
        bytes_size: outputString.length,
        injection_scan: 'CLEAN',
      },
    }),
  );

  return c.json({ status: 'COMMITTED' }, 200);
});

/** Legacy Phase 2 settlement (header-based) */
app.post('/v1/settle', async (c) => {
  const headers = extractHeaders(c.req.raw, true);
  if (headers instanceof Response) return headers;

  const body = await parseBody(c.req.raw);
  if (body instanceof Response) return body;

  if (body.phase !== 'COMMITTED' && body.phase !== 'ABORTED') {
    return jsonError('INVALID_PHASE', 'Settle requires phase COMMITTED or ABORTED', 400);
  }

  const tx_id = headers.transactionId!;
  const redis = createRedisClient(c.env);

  if (body.phase === 'ABORTED') {
    await rollbackBudget(redis, headers.agentId, body.cost, true);
  } else {
    const outputError = detectIndirectPromptInjection(body.result);
    if (outputError) {
      await rollbackBudget(redis, headers.agentId, body.cost, true);
      c.executionCtx.waitUntil(
        updateLedgerState(c.env, tx_id, {
          transaction_state: 'ABORTED',
          error_message: 'INDIRECT_PROMPT_INJECTION_DETECTED in tool output payload',
        }),
      );
      return outputError;
    }
  }

  c.executionCtx.waitUntil(
    updateLedgerState(c.env, tx_id, {
      transaction_state: body.phase,
      tool_output_summary:
        body.phase === 'COMMITTED'
          ? { injection_scan: 'CLEAN' }
          : undefined,
      error_message:
        body.phase === 'ABORTED' ? 'Tool execution aborted' : undefined,
    }),
  );

  return c.json({ status: body.phase, transaction_id: tx_id }, 200);
});

/** Client lease heartbeat pulse */
app.post('/v1/tx/:id/heartbeat', async (c) => {
  const txId = c.req.param('id');
  const redis = createRedisClient(c.env);
  const renewed = await renewLease(redis, txId);
  if (renewed) {
    return c.json({ status: 'LEASE_RENEWED' });
  }
  return c.json({ status: 'TERMINATED_OR_SETTLED' });
});

/** Human approval polling with lease abandonment detection */
app.get('/v1/tx/:id', async (c) => {
  const txId = c.req.param('id');
  const redis = createRedisClient(c.env);
  const meta = await loadTxMeta(redis, txId);

  if (meta) {
    const abandoned = await checkLeaseAbandoned(
      redis,
      c.env,
      txId,
      meta.agent_id,
      meta.cost,
    );
    if (abandoned) {
      return c.json({ tx_id: txId, state: abandoned });
    }
  }

  const state = await redis.get(txKey(txId));
  return c.json({ tx_id: txId, state: state ?? 'EXPIRED_OR_NOT_FOUND' });
});

/** Operator manual settlement with lease-gated approval */
app.post('/v1/tx/:id/settle', async (c) => {
  const txId = c.req.param('id');
  const { decision } = await c.req.json<{ decision?: string }>();
  const redis = createRedisClient(c.env);

  const targetState = await redis.get(txKey(txId));
  if (targetState !== 'PENDING') {
    return jsonError('TRANSACTION_NOT_PENDING', 'Transaction is not in PENDING state', 400);
  }

  const meta = await loadTxMeta(redis, txId);

  if (decision === 'APPROVED') {
    const lease = await redis.get(`lease:${txId}`);
    if (!lease) {
      if (meta) {
        await abandonPendingTransaction(
          redis,
          c.env,
          txId,
          meta.agent_id,
          meta.cost,
          'Approval rejected: client lease expired during pending review',
        );
      }
      return c.json({ tx_id: txId, state: 'CLIENT_ABANDONED' }, 202);
    }
    await markAuthorized(redis, txId);
    return c.json({ result: 'SETTLED_APPROVED', tx_id: txId, state: 'AUTHORIZED' });
  }

  if (meta) {
    await rollbackBudget(redis, meta.agent_id, meta.cost, true);
  }
  await redis.del(txKey(txId), `lease:${txId}`, `txmeta:${txId}`);
  c.executionCtx.waitUntil(
    updateLedgerState(c.env, txId, {
      transaction_state: 'ABORTED',
      error_message: 'Manual administrative rejection issued by supervisor',
    }),
  );
  return c.json({ result: 'SETTLED_DENIED', tx_id: txId, state: 'ABORTED' });
});

export default app;
