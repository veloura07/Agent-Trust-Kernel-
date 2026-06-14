import { Hono } from 'hono'
import { HTTPException } from 'hono/http-exception'

const app = new Hono()

interface Env {
  UPSTASH_REDIS_REST_URL: string
  UPSTASH_REDIS_REST_TOKEN: string
  ATK_MASTER_ENCRYPTION_SECRET: string
  AI: any
  REDIS_KEY_PREFIX?: string
}

async function runRedisCommand(env: Env, payload: any[]): Promise<any> {
  const response = await fetch(env.UPSTASH_REDIS_REST_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.UPSTASH_REDIS_REST_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`Upstash Error: ${response.statusText}`)
  const data = await response.json()
  return data.result
}

function bufferToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}

app.post('/v1/verify/prepare', async (c) => {
  const env = c.env as Env
  const payload = await c.req.json<any>()
  const clientIp = c.req.raw.headers.get('cf-connecting-ip') ?? '127.0.0.1'

  const schema_version = payload.schema_version ?? ''
  const agent_id = payload.agent_id ?? ''
  const tool_name = payload.tool_name ?? ''
  const argument_keys = payload.argument_keys ?? []
  const argument_values = payload.argument_values ?? []
  const nonce = payload.nonce ?? ''
  const timestamp = payload.timestamp ?? ''
  const signatures = payload.signatures ?? []
  const estimated_cost = payload.estimated_cost ?? 0
  const intent_passport = payload.intent_passport ?? {}
  const genome_signature = payload.genome_signature ?? {}
  const idempotency_key = payload.idempotency_key ?? ''

  if (schema_version !== '1.0') return c.text('UNSUPPORTED_SCHEMA_VERSION', 400)

  // --- THE ULTRA-LOW LATENCY HOT PATH (RING 1-6 ATOMIC LUA GATE) ---
  const hotPathScript = `
    local nonceKey = KEYS[1]
    local budgetKey = KEYS[2]
    local rateKey = KEYS[3]
    local lifecycleKey = KEYS[4]
    local idempotencyKey = KEYS[5]
    local badIpSetKey = KEYS[6]

    -- Ring 1: IP reputation gating early checkpoint
    if redis.call('SISMEMBER', badIpSetKey, ARGV[3]) == 1 then
      return {"ERR_IP_REPUTATION_BLOCKED"}
    end

    -- Ring 2: Idempotency Check (Prevent duplicate execution)
    if redis.call('EXISTS', idempotencyKey) == 1 then
      return {"ERR_IDEMPOTENT", redis.call('GET', idempotencyKey)}
    end

    -- Ring 3: Nonce Replay Prevention
    if redis.call('EXISTS', nonceKey) == 1 then return {"ERR_NONCE_REPLAY"} end
    redis.call('SET', nonceKey, '1', 'EX', 3600)

    -- Ring 4: Lifecycle Quarantine Check
    local state = redis.call('GET', lifecycleKey) or "CERTIFIED"
    if state == "SUSPENDED" or state == "RETIRED" then return {"ERR_LIFECYCLE_STATE_ISOLATED"} end

    -- Ring 5: Daily Budget Thresholds
    local currentBudget = tonumber(redis.call('GET', budgetKey) or "0.0")
    local updatedBudget = currentBudget + tonumber(ARGV[1])
    if updatedBudget > 500.0 then return {"ERR_DAILY_BUDGET_EXHAUSTED"} end
    redis.call('SET', budgetKey, tostring(updatedBudget))

    -- Ring 6: Velocity Limits Burst Tracking
    local velocity = redis.call('INCR', rateKey)
    if velocity == 1 then redis.call('EXPIRE', rateKey, 60) end
    if velocity > 120 then return {"ERR_VELOCITY_THROTTLED"} end

    -- Cache current idempotency map reservation token
    redis.call('SET', idempotencyKey, ARGV[2], 'EX', 86400)

    return {"OK"}
  `

  const prefix = env.REDIS_KEY_PREFIX ?? ''
  const nonceKey = `${prefix}nonce:${agent_id}:${nonce}`
  const budgetKey = `${prefix}budget:${agent_id}:daily`
  const rateKey = `${prefix}rate:${agent_id}:window`
  const lifecycleKey = `${prefix}lifecycle:${agent_id}:state`
  const idemKey = `${prefix}idem:${agent_id}:${idempotency_key}`
  const badIpSetKey = `${prefix}bad_ips`

  const targetTxId = crypto.randomUUID()

  try {
    const result = await runRedisCommand(env, [
      'EVAL', hotPathScript, '6',
      nonceKey, budgetKey, rateKey, lifecycleKey, idemKey, badIpSetKey,
      String(estimated_cost), targetTxId, clientIp
    ])

    if (result && Array.isArray(result)) {
      const status = result[0]
      if (status !== 'OK') {
        if (status === 'ERR_IDEMPOTENT') {
          return c.json({ tx_id: result[1], status: 'IDEMPOTENT_RESUBMISSION_BYPASS' })
        }
        return c.text(`ACCESS DENIED: ${status}`, 403)
      }
    } else {
      return c.text('FAIL_CLOSED_STATE_UNRECOGNIZED_VERDICT', 500)
    }
  } catch (err) {
    return c.text('FAIL_CLOSED_STATE_CACHE_UNREACHABLE', 500)
  }

  // Cryptographic Signature Verification Node
  let canonicalPayloadBlock = ''
  for (let i = 0; i < argument_keys.length; i++) {
    const key = String(argument_keys[i] ?? '').trim()
    const val = String(argument_values[i] ?? '').trim()
    canonicalPayloadBlock += `${key}:${val}\n`
  }
  
  const sortedPassportKeys = Object.keys(intent_passport).sort()
  const sortedPassport: Record<string, any> = {}
  for (const k of sortedPassportKeys) { sortedPassport[k] = intent_passport[k] }
  
  const sortedGenomeKeys = Object.keys(genome_signature).sort()
  const sortedGenome: Record<string, any> = {}
  for (const k of sortedGenomeKeys) { sortedGenome[k] = genome_signature[k] }

  const canonicalWireString = `${nonce}\n${timestamp}\n${agent_id}\n${tool_name}\n${JSON.stringify(sortedPassport)}\n${JSON.stringify(sortedGenome)}\n${canonicalPayloadBlock.trim()}`
  
  const stringEncoder = new TextEncoder()
  const baseEpoch = Math.floor(parseInt(timestamp, 10) / 86400)
  let signatureVerified = false

  for (const epoch of [baseEpoch, baseEpoch - 1, baseEpoch + 1]) {
    try {
      const masterKey = await crypto.subtle.importKey('raw', stringEncoder.encode(env.ATK_MASTER_ENCRYPTION_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      const derived = await crypto.subtle.sign('HMAC', masterKey, stringEncoder.encode(`${agent_id}:${epoch}`))
      const opKey = await crypto.subtle.importKey('raw', derived, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      const signed = await crypto.subtle.sign('HMAC', opKey, stringEncoder.encode(canonicalWireString))
      if (signatures.includes(bufferToHex(signed))) {
        signatureVerified = true
        break
      }
    } catch (e) {}
  }

  if (!signatureVerified) {
    await runRedisCommand(env, ['INCRBYFLOAT', budgetKey, String(-estimated_cost)])
    await runRedisCommand(env, ['DEL', idemKey])
    return c.text('SIGNATURE_VERIFICATION_FAILED', 401)
  }

  // --- ASYMMETRIC DECOUPLED COLD PATH ---
  c.executionCtx.waitUntil(
    (async () => {
      try {
        const eventPayload = { schema_version: '1.0', tx_id: targetTxId, agent_id, tool_name, estimated_cost, timestamp: Date.now() }
        await runRedisCommand(env, ['RPUSH', `${prefix}events:${agent_id}:stream`, JSON.stringify({
          tx_id: targetTxId, type: 'PREPARE_REQUESTED', payload: eventPayload
        })])
      } catch (asyncErr) {}
    })()
  )

  return c.json({ tx_id: targetTxId, status: 'AUTHORIZED' })
})

app.post('/v1/verify/commit', async (c) => {
  const env = c.env as Env
  const payload = await c.req.json<any>()
  const { tx_id, agent_id, status, payload_content_hash } = payload

  c.executionCtx.waitUntil(
    (async () => {
      try {
        const prefix = env.REDIS_KEY_PREFIX ?? ''
        await runRedisCommand(env, ['RPUSH', `${prefix}events:${agent_id}:stream`, JSON.stringify({
          tx_id, type: status, payload_content_hash, timestamp: Date.now()
        })])
        if (status === 'ABORTED') {
          await runRedisCommand(env, ['INCRBYFLOAT', `${prefix}budget:${agent_id}:daily`, '-0.001'])
        }
      } catch (err) {}
    })()
  )

  return c.json({ tx_id, state: 'LEDGER_DISPATCHED' })
})

export default app
