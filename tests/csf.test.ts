import { describe, it, expect } from 'vitest';
import {
  buildSigningString,
  canonicalizeArgs,
  deriveTimeGatedSecret,
  computeSignature,
  getCurrentEpoch,
} from '../src/crypto/csf';

/** Shared test vectors — must match sdk/tests/test_vectors.json */
export const TEST_VECTORS = {
  masterSecret: 'test-master-secret-key-32bytes!!',
  agentId: 'autonomous_ops_worker',
  epoch: 19675,
  nonce: 'a1b2c3d4e5f6789012345678901234ab',
  timestamp: '1700000000',
  toolName: 'execute_web_scrape',
  args: { depth_limit: 2, url: 'https://example.com' },
  expectedCanonicalArgs: '{"depth_limit":2,"url":"https://example.com"}',
  expectedSignature: '8a45c400f8c4f01b6b0bdebdd436414e3fdc4b6c600b2317c33546b7e9eff7c5',
};

describe('CSF canonical serialization (v4 epoch keys)', () => {
  it('sorts keys lexicographically', () => {
    expect(canonicalizeArgs(TEST_VECTORS.args)).toBe(
      TEST_VECTORS.expectedCanonicalArgs,
    );
  });

  it('builds signing string with newline delimiters', () => {
    const signing = buildSigningString(
      TEST_VECTORS.nonce,
      TEST_VECTORS.timestamp,
      TEST_VECTORS.agentId,
      TEST_VECTORS.toolName,
      TEST_VECTORS.args,
    );
    expect(signing).toBe(
      `${TEST_VECTORS.nonce}\n${TEST_VECTORS.timestamp}\n${TEST_VECTORS.agentId}\n${TEST_VECTORS.toolName}\n${TEST_VECTORS.expectedCanonicalArgs}`,
    );
  });

  it('derives epoch from timestamp', () => {
    expect(getCurrentEpoch(parseInt(TEST_VECTORS.timestamp, 10))).toBe(
      TEST_VECTORS.epoch,
    );
  });

  it('produces deterministic v4 signature hex', async () => {
    const agentSecret = await deriveTimeGatedSecret(
      TEST_VECTORS.masterSecret,
      TEST_VECTORS.agentId,
      TEST_VECTORS.epoch,
    );
    const signingString = buildSigningString(
      TEST_VECTORS.nonce,
      TEST_VECTORS.timestamp,
      TEST_VECTORS.agentId,
      TEST_VECTORS.toolName,
      TEST_VECTORS.args,
    );
    const signature = await computeSignature(agentSecret, signingString);
    expect(signature).toBe(TEST_VECTORS.expectedSignature);
  });
});
