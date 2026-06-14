import type { RedisClient } from '../redis/client';
import { budgetKeyEpoch } from '../redis/client';
import { rollbackBudget } from '../redis/budget';
import type { Env } from '../types';
import { updateLedgerState } from '../supabase/ledger';

export const LEASE_TTL_SECONDS = 15;
export const PENDING_TX_TTL_SECONDS = 300;
export const AUTHORIZED_TX_TTL_SECONDS = 60;

export function leaseKey(txId: string): string {
  return `lease:${txId}`;
}

export function txKey(txId: string): string {
  return `tx:${txId}`;
}

export async function renewLease(redis: RedisClient, txId: string): Promise<boolean> {
  const state = await redis.get(txKey(txId));
  if (state !== 'PENDING') return false;
  await redis.set(leaseKey(txId), 'ACTIVE', LEASE_TTL_SECONDS);
  return true;
}

export async function initializePendingLease(
  redis: RedisClient,
  txId: string,
): Promise<void> {
  await redis.set(txKey(txId), 'PENDING', PENDING_TX_TTL_SECONDS);
  await redis.set(leaseKey(txId), 'ACTIVE', LEASE_TTL_SECONDS);
}

export async function markAuthorized(
  redis: RedisClient,
  txId: string,
): Promise<void> {
  await redis.set(txKey(txId), 'AUTHORIZED', AUTHORIZED_TX_TTL_SECONDS);
}

export async function abandonPendingTransaction(
  redis: RedisClient,
  env: Env,
  txId: string,
  agentId: string,
  cost: number,
  reason: string,
): Promise<void> {
  await rollbackBudget(redis, agentId, cost, true);
  await redis.del(txKey(txId), leaseKey(txId));
  await updateLedgerState(env, txId, {
    transaction_state: 'CLIENT_ABANDONED',
    error_message: reason,
  });
}

export async function checkLeaseAbandoned(
  redis: RedisClient,
  env: Env,
  txId: string,
  agentId: string,
  cost: number,
): Promise<'CLIENT_ABANDONED' | null> {
  const state = await redis.get(txKey(txId));
  const lease = await redis.get(leaseKey(txId));

  if (state === 'PENDING' && !lease) {
    await abandonPendingTransaction(
      redis,
      env,
      txId,
      agentId,
      cost,
      'Client container dropped lease heartbeat during pending review',
    );
    return 'CLIENT_ABANDONED';
  }
  return null;
}

export function revocationKey(agentId: string, epoch: number): string {
  return `revocation:${agentId}:${epoch}`;
}
