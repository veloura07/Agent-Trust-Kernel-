import { jsonError } from './headers';

const INJECTION_PATTERN =
  /system\s+instruction|override\s+policy|ignore\s+previous/g;

export function detectInputInjection(args: Record<string, unknown>): Response | null {
  const payloadString = JSON.stringify(args).toLowerCase();
  if (INJECTION_PATTERN.test(payloadString)) {
    return jsonError(
      'PROMPT_INJECTION_DETECTED',
      'Payload parameters matched prompt injection override fingerprints',
      403,
    );
  }
  return null;
}

/** v4 Semantic Response Guard — scan tool output before release to LLM context */
export function detectIndirectPromptInjection(output: unknown): Response | null {
  const outputString = JSON.stringify(output ?? {}).toLowerCase();
  if (INJECTION_PATTERN.test(outputString)) {
    return jsonError(
      'INDIRECT_PROMPT_INJECTION_DETECTED',
      'Phase 2 payload inspection flagged prompt-override keywords in tool output',
      403,
    );
  }
  return null;
}
