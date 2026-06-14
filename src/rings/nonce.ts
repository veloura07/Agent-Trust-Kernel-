import type { RedisClient } from '../redis/client';
import { jsonError } from './headers';

export async function ring3CheckNonce(
  redis: RedisClient,
  agentId: string,
  nonce: string,
): Promise<Response | null> {
  const key = `nonce:${agentId}:${nonce}`;
  const isUnique = await redis.setNx(key, '1', 3600);
  if (!isUnique) {
    return jsonError(
      'NONCE_REPLAY_DETECTED',
      'Transaction nonce was already consumed within the past hour',
      403,
    );
  }
  return null;
}

export async function ring3CheckNonceLegacy(
  redis: RedisClient,
  nonce: string,
): Promise<Response | null> {
  const key = `nonce:${nonce}`;
  const isUnique = await redis.setNx(key, '1', 3600);
  if (!isUnique) {
    return jsonError(
      'NONCE_REPLAY_DETECTED',
      'Transaction nonce was already consumed within the past hour',
      403,
    );
  }
  return null;
}
