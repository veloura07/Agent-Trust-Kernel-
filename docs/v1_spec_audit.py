"""
AgentGuard v1 Specification — Bug Audit
==========================================

Bugs found in the provided specification:

1. **`asyncio.create_task()` in a synchronous method (CRASH)**
   `check_capability_gate()` is synchronous but calls `asyncio.create_task()`.
   This works only if called from within a running event loop (i.e., from an async
   function). If ever called from a sync context, it raises RuntimeError.
   Fix: Separate plugin dispatch into an async method; have the `wrapper` schedule it.

2. **Walrus operator misuse in dict literal (CONFUSING, not a bug)**
   `"tx_id": generationTxId := generation_tx_id`
   This creates a local variable `generationTxId` via walrus but it is never read
   again. The result is just the variable `generation_tx_id` being assigned to the
   key. Removed the walrus; used the variable directly.

3. **`hmac.new()` vs `hmac.new()` — legacy API (MINOR)**
   `hmac.new(key, msg, digestmod)` is the legacy positional form. The correct modern
   form uses the same signature but should be called as `hmac.new(key, msg=...,
   digestmod=...)`. Works in Python 3.10+ but flagged for clarity.

4. **Walrus in `CapabilityToken.verify()` creates unused variable (DEAD CODE)**
   `raw_string := raw_claims.encode("utf-8")` creates `raw_string` which is
   immediately shadowed by the local encode call and never used again.
   Fix: removed walrus; inline the encode.

5. **`asyncio.create_task()` in `settle_transaction()` same issue as #1 (CRASH)**
   Same pattern — synchronous method calling `asyncio.create_task()`.
   Fix: same as #1 — push scheduling to the async wrapper.

6. **`LocalFlatFileAuditLogger` uses synchronous `open()` in an async method (BLOCKING)**
   Blocking file I/O in an `async def process_event()` blocks the event loop.
   Fix: use `aiofiles` for non-blocking file writes.

7. **`AgentBehaviorDnaTracker` uses `list.pop(0)` as a ring buffer (O(n))**
   `list.pop(0)` is O(n). Replace with `collections.deque(maxlen=100)`.
   Fix: use `deque`.

8. **Budget tracking is not thread-safe (RACE CONDITION)**
   `self.budget_consumed += cost` without a lock allows races in concurrent async use.
   Fix: wrap in asyncio.Lock or use an atomic pattern.

9. **`test_cryptographic_capability_token_bypass` is a security regression test (LOGIC ERROR)**
   The test asserts that a valid token bypasses financial limits and allows a
   $5,000,000 transfer. A capability token should bypass *policy evaluation* (rings
   2–4) not budget limits. Budget exhaustion is a hard financial control and must
   never be bypassed by a capability token.
   Fix: the test is corrected to use a reasonable amount that is within budget.
"""
