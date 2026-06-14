import { describe, it, expect } from 'vitest';
import { extractHeaders, jsonError } from '../src/rings/headers';
import { ring4CheckTimestamp } from '../src/rings/signature';
import { evaluatePolicy, evaluateRule } from '../src/rings/budget-policy';
import type { AgentPolicy, PolicyRule } from '../src/types';

describe('Ring 1: Header extraction', () => {
  it('returns MISSING_HEADERS when required headers absent', () => {
    const req = new Request('http://localhost/v1/authorize', { method: 'POST' });
    const result = extractHeaders(req);
    expect(result).toBeInstanceOf(Response);
    if (result instanceof Response) {
      expect(result.status).toBe(401);
    }
  });

  it('extracts valid headers', () => {
    const req = new Request('http://localhost/v1/authorize', {
      method: 'POST',
      headers: {
        'X-ATK-Agent-Id': 'autonomous_ops_worker',
        'X-ATK-Nonce': 'abc123',
        'X-ATK-Timestamp': '1700000000',
        'X-ATK-Signature': 'deadbeef',
      },
    });
    const result = extractHeaders(req);
    expect(result).not.toBeInstanceOf(Response);
    if (!(result instanceof Response)) {
      expect(result.agentId).toBe('autonomous_ops_worker');
    }
  });
});

describe('Ring 4: Timestamp validation', () => {
  it('rejects timestamps outside 300s window', () => {
    const old = String(Math.floor(Date.now() / 1000) - 400);
    const result = ring4CheckTimestamp(old);
    expect(result).toBeInstanceOf(Response);
    if (result instanceof Response) {
      expect(result.status).toBe(401);
    }
  });

  it('accepts current timestamp', () => {
    const now = String(Math.floor(Date.now() / 1000));
    expect(ring4CheckTimestamp(now)).toBeNull();
  });
});

describe('Ring 5: Policy compiler', () => {
  const policy: AgentPolicy = {
    capabilities: [
      {
        tool: 'execute_web_scrape',
        rules: [
          {
            field: 'depth_limit',
            operator: 'GREATER_THAN',
            value: 3,
            on_violation: 'BLOCK',
          },
        ],
      },
      {
        tool: 'execute_financial_transfer',
        rules: [
          {
            field: 'amount_usd',
            operator: 'GREATER_THAN',
            value: 100.0,
            on_violation: 'ESCALATE',
          },
        ],
      },
    ],
  };

  it('allows compliant args', () => {
    const result = evaluatePolicy(policy, 'execute_web_scrape', { depth_limit: 2 });
    expect(result.allowed).toBe(true);
  });

  it('blocks policy violations', () => {
    const result = evaluatePolicy(policy, 'execute_web_scrape', { depth_limit: 5 });
    expect(result.allowed).toBe(false);
    expect(result.escalate).toBe(false);
  });

  it('escalates high-value transfers', () => {
    const result = evaluatePolicy(
      policy,
      'execute_financial_transfer',
      { amount_usd: 750 },
    );
    expect(result.escalate).toBe(true);
  });

  it('denies unknown tools', () => {
    const result = evaluatePolicy(policy, 'unknown_tool', {});
    expect(result.allowed).toBe(false);
  });
});

describe('Error responses', () => {
  it('returns structured JSON error', async () => {
    const resp = jsonError('MISSING_HEADERS', 'test message', 401);
    const body = (await resp.json()) as { error: string };
    expect(body.error).toBe('MISSING_HEADERS');
    expect(resp.status).toBe(401);
  });
});
