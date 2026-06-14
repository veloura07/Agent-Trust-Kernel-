import {
  buildSigningString,
  computeSignature,
  timingSafeEqual,
} from '../crypto/csf';
import { jsonError } from './headers';

const TIMESTAMP_WINDOW_SECONDS = 300;
const TIMESTAMP_WINDOW_MS = 300_000;

export function ring4CheckTimestamp(timestamp: string): Response | null {
  const clientTime = parseInt(timestamp, 10);
  if (Number.isNaN(clientTime)) {
    return jsonError('EXPIRED_TIMESTAMP_WINDOW', 'Invalid timestamp format', 401);
  }

  // Support both seconds and milliseconds
  const isMilliseconds = timestamp.length >= 13;
  if (isMilliseconds) {
    const drift = Math.abs(Date.now() - clientTime);
    if (drift > TIMESTAMP_WINDOW_MS) {
      return jsonError(
        'EXPIRED_TIMESTAMP_WINDOW',
        'Request timestamp is outside the 300-second window',
        401,
      );
    }
  } else {
    const currentTime = Math.floor(Date.now() / 1000);
    if (Math.abs(currentTime - clientTime) > TIMESTAMP_WINDOW_SECONDS) {
      return jsonError(
        'EXPIRED_TIMESTAMP_WINDOW',
        'Request timestamp is outside the 300-second window',
        401,
      );
    }
  }
  return null;
}

export async function ring4VerifySignature(
  agentSecret: ArrayBuffer,
  nonce: string,
  timestamp: string,
  agentId: string,
  toolName: string,
  args: Record<string, unknown>,
  signature: string,
): Promise<Response | null> {
  const signingString = buildSigningString(
    nonce,
    timestamp,
    agentId,
    toolName,
    args,
  );
  const expected = await computeSignature(agentSecret, signingString);
  if (!timingSafeEqual(expected, signature.toLowerCase())) {
    return jsonError(
      'SIGNATURE_VERIFICATION_FAILED',
      'HMAC signature does not match the computed edge token',
      401,
    );
  }
  return null;
}

export function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

export async function ring4VerifySignatureWithKey(
  agentKey: CryptoKey,
  nonce: string,
  timestamp: string,
  agentId: string,
  toolName: string,
  args: Record<string, unknown>,
  signature: string,
): Promise<Response | null> {
  const signingString = buildSigningString(
    nonce,
    timestamp,
    agentId,
    toolName,
    args,
  );
  const valid = await crypto.subtle.verify(
    'HMAC',
    agentKey,
    hexToBytes(signature),
    new TextEncoder().encode(signingString),
  );
  if (!valid) {
    return jsonError(
      'SIGNATURE_VERIFICATION_FAILED',
      'HMAC signature does not match the computed edge token',
      401,
    );
  }
  return null;
}

import { detectInputInjection } from './output-guard';

export function detectPromptInjection(args: Record<string, unknown>): Response | null {
  return detectInputInjection(args);
}

export { detectIndirectPromptInjection } from './output-guard';
