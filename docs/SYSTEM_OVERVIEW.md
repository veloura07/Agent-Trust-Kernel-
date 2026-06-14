# System Overview: Safe Execution Layer (SEL) v3

The Safe Execution Layer (SEL) v3 is a zero-trust runtime proxy and verification plane designed for autonomous AI agents. It shifts the problem from abstract "AI Governance" into a concrete, low-latency, fail-closed network and infrastructure boundary control plane.

## 1. The Core Philosophy

Traditional application security assumes that the executing software code is well-behaved and that vulnerabilities occur from malicious user inputs. **AI agents invert this threat model.** Because an agent relies on non-deterministic Large Language Models (LLMs) interpreting untrusted external context (emails, web pages, document uploads), the agent runtime is constantly exposed to **Prompt Injection, Semantic Drift, and Malicious Token Escalation**.

SEL v3 operates on a foundational axiom: **The agent runtime environment must be treated as completely untrusted and compromised.** No security check running inside the same Python process as the agent loop can be fully guaranteed. Security, resource budgeting, and capability restrictions must be calculated externally at the serverless network edge before any external API mutation occurs.

---

## 2. System Architecture & Component Mapping

The platform uses a decoupled, serverless topology designed to fit within standard infrastructure free-tiers while ensuring sub-10ms validation latency at the edge.

```text
+---------------------------------------------------------------------------------+
|                         UNTRUSTED RUNTIME ENVIRONMENT                           |
|                                                                                 |
|   +-----------------------+                    +----------------------------+   |
|   |   Agent Logic Loop    | <----------------- |    SEL Python Client SDK   |   |
|   +-----------------------+                    +----------------------------+   |
|               |                                              |                  |
|               | 1. Intercepted Tool Execution                | 2. Signed CSF    |
|               v                                              v                  |
+--------------------------------------------------------------|------------------+
                                                               | (TLS HTTP POST)
                                                               v
+---------------------------------------------------------------------------------+
|                         STATELESS NETWORK EDGE CONTROL                          |
|                                                                                 |
|      +-------------------------------------------------------------------+      |
|      |               Cloudflare Workers Edge Interceptor                 |      |
|      |                                                                   |      |
|      |  * Ring 1: Header Schema & Key Extraction                         |      |
|      |  * Ring 2: Deterministic HKDF Secret Derivation                   |      |
|      |  * Ring 3: Sliding-Window Redis Nonce Check                       |      |
|      |  * Ring 4: WebCrypto Signature Integrity Matching                 |      |
|      |  * Ring 5: Atomic Optimistic Budget & Capability Verification     |      |
|      +-------------------------------------------------------------------+      |
+---------------------------------------------------------------------------------+
             |                                                |
    (Atomic Redis Commands)                         (Async Log Transmissions)
             v                                                v
+---------------------------+                    +----------------------------+
|    STATE MEMORY CACHE     |                    |  IMMUTABLE LOG PERSISTENCE |
|                           |                    |                            |
| Upstash Redis Serverless  |                    |  Supabase Cloud Postgres   |
+---------------------------+                    +----------------------------+
```

## Infrastructure Component Breakdown

**The Client SDK (Python):** A zero-dependency runtime decorator and context manager that hooks into agent tool definitions. It calculates canonical payload representations, signs them using derived credentials, and coordinates the Two-Phase Commit transaction lifecycle.

**The Edge Interceptor (Cloudflare Workers):** A stateless engine built with Hono. It derives encryption secrets locally using a master secret key, processes incoming requests, evaluates constraints using an inline policy compiler, and manages transaction caching.

**The State Cache Hub (Upstash Redis):** A low-latency serverless memory store used to evaluate single-use nonces, monitor sliding-window velocity rate limits, track active human approval flags, and process atomic budget balances.

**The Analytics Ledger (Supabase Postgres):** A persistent database storage layer that archives immutable transaction states, append-only memory lineage markers, and long-term compliance metrics out-of-band via background execution processes.
