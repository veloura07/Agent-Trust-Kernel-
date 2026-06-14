import type { RedisClient } from './client';
import { budgetKey, budgetKeyEpoch } from './client';

export interface BudgetResult {
  ok: boolean;
  key: string;
  total: number;
}

export async function reserveBudget(
  redis: RedisClient,
  agentId: string,
  cost: number,
  dailyLimit: number,
  useEpochKey = false,
): Promise<BudgetResult> {
  const key = useEpochKey ? budgetKeyEpoch(agentId) : budgetKey(agentId);
  const total = await redis.incrByFloat(key, cost);

  if (total > dailyLimit) {
    await redis.incrByFloat(key, -cost);
    return { ok: false, key, total: total - cost };
  }

  return { ok: true, key, total };
}

export async function rollbackBudget(
  redis: RedisClient,
  agentId: string,
  cost: number,
  useEpochKey = false,
): Promise<number> {
  const key = useEpochKey ? budgetKeyEpoch(agentId) : budgetKey(agentId);
  return redis.incrByFloat(key, -cost);
}
