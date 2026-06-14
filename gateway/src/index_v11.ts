import { Hono } from 'hono'

const app = new Hono()

interface Env {
  UPSTASH_REDIS_REST_URL: string
  UPSTASH_REDIS_REST_TOKEN: string
  ATK_MASTER_ENCRYPTION_SECRET: string
  AI: any 
}

async function runRedisCommand(env: Env, commandPayload: any[]): Promise<any> {
  const response = await fetch(env.UPSTASH_REDIS_REST_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.UPSTASH_REDIS_REST_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(commandPayload),
  })
  if (!response.ok) {
    throw new Error(`Upstash Cache Failure: ${response.statusText}`)
  }
  const data = await response.json()
  return data.result
}

function convertBufferToHexStr(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2, '0')).join('')
}

app.post('/v1/verify/prepare', async (c) => {
  const env = c.env as Env
  let payload: any
  
  try { 
    payload = await c.req.json() 
  } catch (err) { 
    return c.text('MALFORMED_JSON_BODY', 400) 
  }
  
  const { 
    agent_id, tool_name, argument_keys, argument_values, nonce, 
    timestamp, signatures, estimated_cost, intent_passport, genome_signature, swarm_governance
  } = payload

  if (!agent_id || !tool_name || !argument_keys || !argument_values || !nonce || !timestamp || !signatures || !estimated_cost || !intent_passport || !genome_signature) {
    return c.text('MISSING_MANDATORY_HOT_PATH_PARAMETERS', 401)
  }

  // --- THE ULTRA LOW LATENCY HOT PATH (RING 1) ---
  // A single, optimized, atomic Lua script execution cell handles all synchronous gates
  const hotPathLuaScript = `
    local nonceKey = KEYS[1]
    local budgetKey = KEYS[2]
    local rateKey = KEYS[3]
    local lifecycleKey = KEYS[4]
    
    if redis.call('EXISTS', nonceKey) == 1 then return {err = "NONCE_REPLAY"} end
    redis.call('SET', nonceKey, '1', 'EX', 3600)
    
    local lifecycleState = redis.call('GET', lifecycleKey) or "CERTIFIED"
    if lifecycleState == "SUSPENDED" or lifecycleState == "RETIRED" then 
      return {err = "LIFECYCLE_STATE_LOCK_ISOLATION"} 
    end
    
    local currentBudget = tonumber(redis.call('GET', budgetKey) or "0.0")
    local policyLimitKey = "policy:" .. ARGV[1] .. ":limit"
    local configuredBudgetLimit = tonumber(redis.call('GET', policyLimitKey) or "500.0")
    
    local updatedProjectedBudget = currentBudget + tonumber(ARGV[2])
    if updatedProjectedBudget > configuredBudgetLimit then 
      return {err = "DAILY_OPERATIONAL_BUDGET_EXHAUSTED"} 
    end
    
    redis.call('SET', budgetKey, tostring(updatedProjectedBudget))
    
    local currentVelocityRate = redis.call('INCR', rateKey)
    if currentVelocityRate == 1 then redis.call('EXPIRE', rateKey, 60) end
    if currentVelocityRate > 120 then return {err = "VELOCITY_THROTTLED"} end
    
    local permissionKey = "perm:" .. ARGV[1] .. ":" .. ARGV[3]
    local isPermitted = redis.call('GET', permissionKey) or "true"
    if isPermitted == "false" then return {err = "CAPABILITY_NOT_PERMITTED"} end
    
    return "HOT_PATH_OK"
  `

  const antiReplayKey = `nonce:${agent_id}:${nonce}`
  const budgetCounterKey = `budget:${agent_id}:daily`
  const slidingRateWindowKey = `rate:${agent_id}:window`
  const agentLifecycleKey = `lifecycle:${agent_id}:state`

  try {
    const hotPathResult = await runRedisCommand(env, [
      'EVAL', hotPathLuaScript, '4', 
      antiReplayKey, budgetCounterKey, slidingRateWindowKey, agentLifecycleKey,
      agent_id, String(estimated_cost), tool_name
    ])
    if (hotPathResult && typeof hotPathResult === 'object' && hotPathResult.err) {
      return c.text(`ACCESS DENIED: ${hotPathResult.err}`, 403)
    }
  } catch (err) { 
    return c.text('FAIL_CLOSED_STATE_CACHE_UNREACHABLE', 500) 
  }

  // Ring 2: Strict Asymmetric Type-Resilient Signature Verification
  let signatureVerified = false
  let canonicalPayloadBlock = ""
  for (let i = 0; i < argument_keys.length; i++) {
    canonicalPayloadBlock += `${argument_keys[i].trim()}:${argument_values[i].trim()}\n`
  }
  
  const sortedPassportKeys = Object.keys(intent_passport).sort()
  const sortedPassport: Record<string, any> = {}
  for (const k of sortedPassportKeys) { sortedPassport[k] = intent_passport[k] }
  
  const minifiedGenomeJson = JSON.stringify(genome_signature)
  const canonicalWireString = `${nonce}\n${timestamp}\n${agent_id}\n${tool_name}\n${JSON.stringify(sortedPassport)}\n${minifiedGenomeJson}\n${canonicalPayloadBlock.trim()}`
  
  const stringEncoder = new TextEncoder()
  const baseEpochSlice = Math.floor(parseInt(timestamp) / 86400)
  const skewTolerantWindows = [baseEpochSlice, baseEpochSlice - 1, baseEpochSlice + 1]

  for (const epoch of skewTolerantWindows) {
    const uniqueContextString = `${agent_id}:${epoch}`
    const masterKeyImport = await crypto.subtle.importKey('raw', stringEncoder.encode(env.ATK_MASTER_ENCRYPTION_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const derivedSecretKeyBuffer = await crypto.subtle.sign('HMAC', masterKeyImport, stringEncoder.encode(uniqueContextString))
    const operationalCryptoKey = await crypto.subtle.importKey('raw', derivedSecretKeyBuffer, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
    const signedHashBuffer = await crypto.subtle.sign('HMAC', operationalCryptoKey, stringEncoder.encode(canonicalWireString))
    if (signatures.includes(convertBufferToHexStr(signedHashBuffer))) { 
      signatureVerified = true
      break 
    }
  }

  if (!signatureVerified) {
    await runRedisCommand(env, ['INCRBYFLOAT', budgetCounterKey, String(-estimated_cost)])
    return c.text('SIGNATURE_VERIFICATION_FAILED', 401)
  }

  const generationTxId = crypto.randomUUID()

  // --- THE DECOUPLED ASYNC COLD PATH ---
  // Dispatch resource-heavy behavioral audits, graph logging, and verification tasks out-of-band
  c.executionCtx.waitUntil(
    (async () => {
      try {
        // 1. Adaptive Approvals & Anomaly Detection Pipeline (Layer 5 Immune System Forest check simulation)
        const trustScoreKey = `trust:${agent_id}:score`
        const currentTrustRating = parseFloat(await runRedisCommand(env, ['GET', trustScoreKey]) || "100.00")
        
        // 2. Risk-Based Reality Verification v2 Sampling Gating
        const serverToolRiskKey = `registry:tool:${tool_name}:risk`
        const toolRiskScore = parseInt(await runRedisCommand(env, ['GET', serverToolRiskKey]) || "5")
        
        if (toolRiskScore >= 7 && currentTrustRating < 90.0) {
          // Trigger out-of-band deep semantic text check evaluation only on verified medium/high risk intersections
          const safetyAssessment = await env.AI.run('@cf/meta/llama-3-8b-instruct', {
            prompt: `Task: Audit parameters against corporate constitutional rules. Reply with SAFE or UNSAFE. Content: ${canonicalPayloadBlock} Goal Objectives: ${intent_passport.goal}`
          })
          if (safetyAssessment?.response?.includes('UNSAFE')) {
            // Log a asynchronous policy violation alarm record token straight to the append-only event log
            await runRedisCommand(env, ['RPUSH', `events:${agent_id}:stream`, JSON.stringify({
              tx_id: generationTxId, type: 'CONSTITUTIONAL_GOVERNANCE_VIOLATION_ALARM', timestamp: Date.now()
            })])
          }
        }
        
        // 3. Append Initial PREPARE sequence context details straight to the Event Sourcing Stream cache
        const initialEventPayload = { tx_id: generationTxId, agent_id, tool_name, estimated_cost, intent_passport, timestamp: Date.now() }
        await runRedisCommand(env, ['RPUSH', `events:${agent_id}:stream`, JSON.stringify({
          tx_id: generationTxId, type: 'PREPARE_REQUESTED', payload: initialEventPayload
        })])
      } catch (asyncColdPathProcessingError) {
        // Cold path background runtime glitches cannot halt or freeze the execution flow of the synchronous hot path loop
      }
    })()
  )

  return c.json({ tx_id: generationTxId, status: 'AUTHORIZED' })
})

app.post('/v1/verify/commit', async (c) => {
  const env = c.env as Env
  const { tx_id, agent_id, status, payload_content_hash } = await c.req.json()

  // Push the final settlement state mutation token directly onto the asynchronous Event stream
  c.executionCtx.waitUntil(
    (async () => {
      const commitEventPayload = { tx_id, status, payload_content_hash, timestamp: Date.now() }
      await runRedisCommand(env, ['RPUSH', `events:${agent_id}:stream`, JSON.stringify({
        tx_id, type: status === 'COMMITTED' ? 'COMMITTED' : 'ABORTED', payload: commitEventPayload
      })])
      
      if (status === 'ABORTED' && agent_id) {
        const budgetCounterKey = `budget:${agent_id}:daily`
        await runRedisCommand(env, ['INCRBYFLOAT', budgetCounterKey, "-0.001"])
      }
    })()
  )

  return c.json({ tx_id, state: 'LEDGER_DISPATCHED' })
})

export default app
