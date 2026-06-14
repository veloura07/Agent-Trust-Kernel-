import { deriveTimeGatedSecret, getCurrentEpoch } from '../crypto/csf';

export { getCurrentEpoch };

export async function deriveAgentCryptoKey(
  masterSecret: string,
  agentId: string,
  epoch?: number,
): Promise<CryptoKey> {
  const resolvedEpoch = epoch ?? getCurrentEpoch();
  const derivedBytes = await deriveTimeGatedSecret(
    masterSecret,
    agentId,
    resolvedEpoch,
  );
  return crypto.subtle.importKey(
    'raw',
    derivedBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  );
}

export async function ring2DeriveSecret(
  masterSecret: string,
  agentId: string,
  epoch?: number,
): Promise<ArrayBuffer> {
  return deriveTimeGatedSecret(
    masterSecret,
    agentId,
    epoch ?? getCurrentEpoch(),
  );
}
