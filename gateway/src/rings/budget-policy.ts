import type { AgentPolicy, PolicyRule } from '../types';
import type { RedisClient } from '../redis/client';
import { reserveBudget, rollbackBudget } from '../redis/budget';
import { jsonError } from './headers';

export async function ring5CheckAgentActive(
  redis: RedisClient,
  agentId: string,
): Promise<Response | null> {
  const cached = await redis.get(`agent:${agentId}:status`);
  if (cached === 'SUSPENDED' || cached === 'false') {
    return jsonError('AGENT_SUSPENDED', 'Agent registration status is suspended', 403);
  }
  return null;
}

export async function loadPolicy(
  redis: RedisClient,
  agentId: string,
): Promise<AgentPolicy | null> {
  const raw = await redis.get(`policy:${agentId}`);
  if (!raw) return null;
  return JSON.parse(raw) as AgentPolicy;
}

export function evaluateRule(
  rule: PolicyRule,
  args: Record<string, unknown>,
): 'PASS' | 'BLOCK' | 'ESCALATE' {
  const value = args[rule.field];
  let violated = false;

  switch (rule.operator) {
    case 'GREATER_THAN':
      violated = typeof value === 'number' && value > (rule.value as number);
      break;
    case 'LESS_THAN':
      violated = typeof value === 'number' && value < (rule.value as number);
      break;
    case 'EQUALS':
      violated = value === rule.value;
      break;
    case 'CONTAINS':
      violated =
        typeof value === 'string' &&
        typeof rule.value === 'string' &&
        value.includes(rule.value);
      break;
  }

  if (!violated) return 'PASS';
  if (rule.on_violation === 'ESCALATE') return 'ESCALATE';
  return 'BLOCK';
}

export interface PolicyEvalResult {
  allowed: boolean;
  escalate: boolean;
  capability?: { tool: string; rules?: PolicyRule[] };
}

export function evaluatePolicy(
  policy: AgentPolicy,
  toolName: string,
  args: Record<string, unknown>,
): PolicyEvalResult {
  const capability = policy.capabilities.find((c) => c.tool === toolName);
  if (!capability) {
    return { allowed: false, escalate: false };
  }

  for (const rule of capability.rules ?? []) {
    const result = evaluateRule(rule, args);
    if (result === 'BLOCK') {
      return { allowed: false, escalate: false, capability };
    }
    if (result === 'ESCALATE') {
      return { allowed: false, escalate: true, capability };
    }
  }

  return { allowed: true, escalate: false, capability };
}

export async function ring5BudgetAndPolicy(
  redis: RedisClient,
  agentId: string,
  toolName: string,
  args: Record<string, unknown>,
  cost: number,
  dailyLimit = 500.0,
): Promise<{ error: Response } | { policyResult: PolicyEvalResult; budgetKey: string }> {
  const agentStatus = await ring5CheckAgentActive(redis, agentId);
  if (agentStatus) return { error: agentStatus };

  const policy = await loadPolicy(redis, agentId);
  if (!policy) {
    return {
      error: jsonError(
        'CAPABILITY_NOT_PERMITTED',
        'No server-side policy found for agent',
        403,
      ),
    };
  }

  const policyResult = evaluatePolicy(policy, toolName, args);
  if (!policyResult.allowed && policyResult.escalate) {
    return { policyResult, budgetKey: '' };
  }
  if (!policyResult.allowed) {
    const hasCapability = policy.capabilities.some((c) => c.tool === toolName);
    return {
      error: jsonError(
        hasCapability ? 'POLICY_VIOLATION_BLOCKED' : 'CAPABILITY_NOT_PERMITTED',
        hasCapability
          ? 'Policy rule blocked execution parameters'
          : 'Requested tool is not registered in agent policy',
        403,
      ),
    };
  }

  const budgetResult = await reserveBudget(redis, agentId, cost, dailyLimit, true);
  if (!budgetResult.ok) {
    return {
      error: jsonError(
        'DAILY_BUDGET_EXHAUSTED',
        'Daily financial balance cap exceeded',
        429,
      ),
    };
  }

  return { policyResult, budgetKey: budgetResult.key };
}

export async function rollbackReservedBudget(
  redis: RedisClient,
  agentId: string,
  cost: number,
): Promise<void> {
  await rollbackBudget(redis, agentId, cost);
}
