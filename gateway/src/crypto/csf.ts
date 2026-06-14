/**
 * Canonical Serialization Format (CSF) — must match Python sdk/sel_v3/csf.py byte-for-byte.
 */

export function canonicalizeArgs(args: Record<string, unknown>): string {
  return JSON.stringify(sortKeys(args));
}

function sortKeys(value: unknown): unknown {
  if (value === null || typeof value !== 'object') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(value as Record<string, unknown>).sort()) {
    sorted[key] = sortKeys((value as Record<string, unknown>)[key]);
  }
  return sorted;
}

export function buildSigningString(
  nonce: string,
  timestamp: string,
  agentId: string,
  toolName: string,
  args: Record<string, unknown>,
): string {
  const canonicalArgs = canonicalizeArgs(args);
  return `${nonce}\n${timestamp}\n${agentId}\n${toolName}\n${canonicalArgs}`;
}

export function getCurrentEpoch(timestampSeconds?: number): number {
  const t = timestampSeconds ?? Math.floor(Date.now() / 1000);
  return Math.floor(t / 86400);
}

export async function deriveTimeGatedSecret(
  masterSecret: string,
  agentId: string,
  epoch: number,
): Promise<ArrayBuffer> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(masterSecret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return crypto.subtle.sign('HMAC', key, encoder.encode(`${agentId}:${epoch}`));
}

/** @deprecated v3 static derivation — use deriveTimeGatedSecret for v4 */
export async function deriveAgentSecret(
  masterSecret: string,
  agentId: string,
): Promise<ArrayBuffer> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(masterSecret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return crypto.subtle.sign('HMAC', key, encoder.encode(agentId));
}

export async function computeSignature(
  agentSecret: ArrayBuffer,
  signingString: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    agentSecret,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const sig = await crypto.subtle.sign(
    'HMAC',
    key,
    new TextEncoder().encode(signingString),
  );
  return bufferToHex(sig);
}

export function bufferToHex(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
