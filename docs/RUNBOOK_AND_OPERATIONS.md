# Operations Manual: Deployment, Threat Mitigation & Troubleshooting

This document outlines the step-by-step procedures for deploying, maintaining, and recovering the SEL v3 infrastructure plane.

---

## 1. Step-by-Step Initial Setup Workflow

Follow this sequence exactly to stand up a zero-cost production control instance:

### Step 1: Database Initialization

Log into your Supabase panel, open the SQL Editor console workspace, paste the entire contents of your `database/schema_v3.sql` script file, and select **Run**. This establishes your schemas, transactional tables, and analytical indexing layouts.

### Step 2: Edge Environment Keys Configuration

Open a terminal inside your gateway directory space and use Wrangler to provision required service variables directly onto the Cloudflare network layer:

```bash
wrangler secret put UPSTASH_REDIS_REST_URL
wrangler secret put UPSTASH_REDIS_REST_TOKEN
wrangler secret put SUPABASE_URL
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
wrangler secret put ATK_MASTER_ENCRYPTION_SECRET
```

### Step 3: Deploy the Edge Gateway

```bash
cd gateway
npm install
npm run deploy
```

For local development:

```bash
npm run dev
```

The worker listens on `http://127.0.0.1:8787` by default.

### Step 4: Authoritative Policy Provisioning

To avoid client-side policy tampering, seed your agent capability limits directly into the Upstash Redis instance. Use a standardized key structure format:

**Redis Key:** `policy:autonomous_ops_worker`

**Redis Value String:**

```json
{
  "capabilities": [
    {
      "tool": "execute_web_scrape",
      "rules": [
        {
          "field": "depth_limit",
          "operator": "GREATER_THAN",
          "value": 3,
          "on_violation": "BLOCK"
        }
      ]
    }
  ]
}
```

Run the seed script:

```bash
python scripts/seed_policy.py
python scripts/seed_agent.py
```

### Step 5: Install the Python SDK

```bash
pip install -e sdk/
```

Wrap agent tools with the `@sel_guard` decorator or use the `client.guard()` context manager.

---

## 2. Platform Core Error Code Dictionary

When the Edge Interceptor Gateway rejects a payload transaction request, it returns a structured JSON frame accompanied by an explicit system error code:

| HTTP Status | Custom Error String | Root Cause Description | Mitigation Action |
|-------------|---------------------|------------------------|-------------------|
| 401 | MISSING_HEADERS | Mandatory validation attributes are missing from the request headers. | Ensure the client SDK is properly initialized and wrapping the target method calls. |
| 401 | EXPIRED_TIMESTAMP_WINDOW | The request timestamp varies by >300,000 ms from the edge gateway's system clock. | Sync system times and verify NTP configuration on the client runtime host. |
| 401 | SIGNATURE_VERIFICATION_FAILED | The calculated HMAC hash does not match the incoming validation signature. | Verify that the secret_key string matching the master encryption seed is identical across deployments. |
| 403 | NONCE_REPLAY_DETECTED | The matching transaction nonce hash was already consumed within the past hour. | Ensure the client cryptographically generates a unique random nonce for every transaction request. |
| 403 | CAPABILITY_NOT_PERMITTED | The requested tool name is not registered in the agent's server-side policy array. | Update the policy configuration stored in Upstash Redis to explicitly include the capability. |
| 403 | AGENT_SUSPENDED | The agent registration status is SUSPENDED. | Update `sel_v3.agent_registry` to restore ACTIVE status after triage. |
| 429 | DAILY_BUDGET_EXHAUSTED | The execution request exceeds the configured daily financial balance cap. | Wait for the daily reset period or manually increase the budget limit within the tracking database. |

---

## 3. Disaster Recovery: Fail-Closed Isolation Architecture

The Client SDK operates on a strict Fail-Closed Strategy. If an internal error occurs, a network connection drops, or a request to the edge gateway times out (>= 5.0 seconds), the SDK blocks further operations immediately.

### Incident Triage Action Protocol

**Isolate the Agent:** If an agent acts erratically, log into your Supabase admin panel or connect via a terminal client to instantly update the agent's registration status row:

```sql
UPDATE sel_v3.agent_registry SET status = 'SUSPENDED' WHERE agent_id = 'target_agent_id';
```

**Instant Propagation:** The Edge Interceptor reads this updated state from the cache on the very next incoming request, blocking any further tool execution queries globally within milliseconds.

**Analyze Post-Mortem Logs:** Review the `sel_v3.execution_ledger` table to audit transaction traces, arguments, and timestamps leading up to the incident to identify the root cause.

---

## 4. Environment Variables Reference

See `.env.example` at the repository root for all required configuration values.

---

## 5. v4 Enterprise Upgrade

Run [`database/schema_v4_patch.sql`](../database/schema_v4_patch.sql) after v3 schema. Expose the `atk_v4` schema in Supabase API settings.

### v4 Key Changes

- **Time-gated keys**: `HMAC-SHA256(Master, AgentID:Epoch)` where `Epoch = floor(unix/86400)`
- **Output sanitization**: Phase 2 via `POST /v1/verify/commit`
- **Lease heartbeats**: `POST /v1/tx/:id/heartbeat` every ~2s during pending review
- **CLIENT_ABANDONED**: Auto-rollback when lease expires during human review

### Revoke Single Agent Key (without master rotation)

```text
SET revocation:autonomous_ops_worker:<epoch> 1 EX 86400
```

### v4 Integration Tests

```powershell
pip install httpx
python sdk/verify_system_v4.py
```
