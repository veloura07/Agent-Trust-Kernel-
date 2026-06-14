import { describe, it, expect, vi, beforeEach } from 'vitest';
import { reserveBudget, rollbackBudget } from '../src/redis/budget';
import { budgetKey } from '../src/redis/client';

function createMockRedis() {
  const store = new Map<string, number>();
  return {
    incrByFloat: vi.fn(async (key: string, increment: number) => {
      const current = store.get(key) ?? 0;
      const next = current + increment;
      store.set(key, next);
      return next;
    }),
    store,
  };
}

describe('Atomic optimistic budget governor', () => {
  let redis: ReturnType<typeof createMockRedis>;

  beforeEach(() => {
    redis = createMockRedis();
  });

  it('allows spend within daily limit', async () => {
    const result = await reserveBudget(redis as any, 'agent_1', 10, 500);
    expect(result.ok).toBe(true);
    expect(result.total).toBe(10);
  });

  it('rolls back when limit exceeded', async () => {
    const key = budgetKey('agent_1');
    redis.store.set(key, 495);
    const result = await reserveBudget(redis as any, 'agent_1', 10, 500);
    expect(result.ok).toBe(false);
    expect(redis.store.get(result.key)).toBe(495);
  });

  it('handles concurrent reservation race', async () => {
    const results = await Promise.all([
      reserveBudget(redis as any, 'agent_1', 250, 500),
      reserveBudget(redis as any, 'agent_1', 250, 500),
      reserveBudget(redis as any, 'agent_1', 10, 500),
    ]);
    const okCount = results.filter((r) => r.ok).length;
    const failCount = results.filter((r) => !r.ok).length;
    expect(okCount).toBe(2);
    expect(failCount).toBe(1);
  });

  it('rollback reduces budget total', async () => {
    await reserveBudget(redis as any, 'agent_1', 50, 500);
    const after = await rollbackBudget(redis as any, 'agent_1', 50);
    expect(after).toBe(0);
  });
});
