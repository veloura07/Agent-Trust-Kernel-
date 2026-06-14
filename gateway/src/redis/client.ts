import type { Env } from '../types';

export class RedisClient {
  constructor(
    private url: string,
    private token: string,
  ) {}

  async command(...args: (string | number)[]): Promise<unknown> {
    const response = await fetch(`${this.url}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(args.map(String)),
    });

    if (!response.ok) {
      throw new Error(`Redis command failed: ${response.status}`);
    }

    const data = (await response.json()) as { result: unknown };
    return data.result;
  }

  async get(key: string): Promise<string | null> {
    const result = await this.command('GET', key);
    return result === null ? null : String(result);
  }

  async set(key: string, value: string, exSeconds?: number): Promise<void> {
    if (exSeconds !== undefined) {
      await this.command('SET', key, value, 'EX', exSeconds);
    } else {
      await this.command('SET', key, value);
    }
  }

  async setNx(key: string, value: string, exSeconds: number): Promise<boolean> {
    const result = await this.command('SET', key, value, 'NX', 'EX', exSeconds);
    return result === 'OK';
  }

  async incrByFloat(key: string, increment: number): Promise<number> {
    const result = await this.command('INCRBYFLOAT', key, increment);
    return parseFloat(String(result));
  }

  async del(...keys: string[]): Promise<void> {
    if (keys.length === 0) return;
    await this.command('DEL', ...keys);
  }
}

export function createRedisClient(env: Env): RedisClient {
  return new RedisClient(env.UPSTASH_REDIS_REST_URL, env.UPSTASH_REDIS_REST_TOKEN);
}

export function budgetKey(agentId: string, date?: Date): string {
  const d = date ?? new Date();
  const day = d.toISOString().slice(0, 10);
  return `budget:${agentId}:${day}`;
}

export function budgetKeyEpoch(agentId: string): string {
  const epoch = Math.floor(Date.now() / 86400000);
  return `budget:${agentId}:${epoch}`;
}
