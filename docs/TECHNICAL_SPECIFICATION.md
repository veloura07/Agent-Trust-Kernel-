# Technical Specification: Core Primitives & Cryptographic Contracts

This document contains the strict implementation standards, cryptographic calculations, and multi-phase execution steps governing the SEL v3 control plane.

---

## 1. Cryptographic Key Derivation (HKDF)

To prevent database lookup bottlenecks (20ms - 60ms of latency per request) and remove database secret choke points, SEL v3 uses a deterministic **Edge-Native Hierarchical Key Derivation Function**.

The Edge Gateway stores a single secure variable, the `ATK_MASTER_ENCRYPTION_SECRET`. When a validation request arrives from a specific agent, the gateway computes that agent's distinct symmetric secret key on the fly using WebCrypto APIs:

```
Agent Secret = HMAC-SHA256(Master Encryption Secret, Agent ID)
```

This derived secret is never stored in a static database. It exists only momentarily within the V8 worker memory isolate to verify the incoming payload signature, ensuring robust security with minimal infrastructure overhead.

---

## 2. Canonical Serialization Format (CSF) & Signature Verification

To eliminate cross-language serialization divergence (where Python's JSON encoder produces alternate string results compared to V8 JavaScript object mapping), payloads are structured using a strict **Canonical Serialization Format (CSF)**.

### The Wire-Protocol Signature String

The signature message string is constructed as an immutable, newline-delimited byte array mapping five structural metrics:

```
Signing String = Nonce || "\n" || Timestamp || "\n" || AgentID || "\n" || ToolName || "\n" || LexicographicalJSONArgs
```

Where `LexicographicalJSONArgs` is a minified JSON string with keys sorted in exact alphabetical order (`separators=(',', ':')`). The final validation signature matches a custom symmetric key signature hash:

```
Signature = HMAC-SHA256(Agent Secret, Signing String)
```

---

## 3. Atomic Optimistic Budget Governor (TOCTOU Resolution)

To resolve Check-Then-Act budget race conditions where high-velocity concurrent tool calls could bypass spending caps, the edge gate uses an **Atomic Optimistic Rollback Pattern**.

```text
    Edge Interceptor Gateway                        Upstash Redis Instance
==================================================================================
1. Receives Request with $Cost
2. Execute Atomic Multi-Command ---------> INCRBYFLOAT budget:key $Cost
3. Evaluate Allocation Result <----------- Returns updated current total cost balance
4. IF Total Cost > $Limit:
     - Revert Allocation Balance --------> INCRBYFLOAT budget:key -$Cost
     - Return HTTP 429 (Budget Block)
   ELSE:
     - Proceed to Policy Engine
```

This pipeline ensures that if an agent attempts multiple tool calls simultaneously, the database states increment atomically. Any execution step that breaches the financial threshold is instantly rolled back, preventing spending cap overruns.

---

## 4. Two-Phase Commit Tool Execution Protocol (2PC)

To prevent "Ghost Receipts"—where a transaction is logged as a success even if the downstream tool fails or times out—SEL v3 splits tool execution into a Two-Phase Commit Protocol.

### Phase 1: Preparation & Authorization

The Client SDK catches an intended tool invocation and sends an AUTHORIZED registration frame to the Edge Interceptor Gateway.

The Edge Gateway validates the identity, checks the nonce, increments the budget balance, evaluates policy rules, and registers the transaction state as AUTHORIZED inside the Postgres ledger.

If successful, the gateway returns an HTTP 200 OK token to release the local execution block.

### Phase 2: Action Settlement & Commit

The SDK runs the underlying tool logic within its environment.

If the tool finishes successfully, the SDK context manager intercepts the response data and sends a final payload settlement frame to the edge gate marked as COMMITTED.

If the tool crashes or throws an exception, the context manager catches the failure, updates the state payload to ABORTED, and sends it to the gate to adjust tracking metrics and release allocated budgets.
