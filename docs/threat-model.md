# ATK v12 Threat Model & Security Boundaries

## 1. Architectural System Boundaries
The Agent Trust Kernel provides a local-first, edge-verified runtime security envelope for autonomous entities. It enforces authorization boundaries at the intercept layer before tool mutation execution occurs.

```text
[Untrusted Agent Process Space] ──(SDK Guard Boundary)──> [Agent Trust Kernel Core]
                                                                        │
                                                           (Hot Path / Cold Path Split)
                                                                        ▼
                                                           [Serverless Edge Proxy / DB]
```

## 2. Definitive Security Invariants
* **Defends Against:**
  * **Indirect Prompt Injection:** Halts data exfiltration vectors and malicious rule override payloads via a deterministic compiled regex firewall before tool processing.
  * **Double-Execution TOCTOU Loops:** Eliminates duplicate actions on network retries using an atomic, serverless cryptographic idempotency cache layer.
  * **Local State Tampering:** Secures local fallback storage layers against process-memory extraction using AES-256 Fernet block encryption.
  * **Swarm Accountability Drift:** Reconstructs explicit causal ancestry paths across multi-parent mesh networks via multi-hop Lineage Passports.

* **Does NOT Defend Against (Out of Scope):**
  * **Compromised Host OS:** If the underlying operating system kernel or container hypervisor is compromised, local process keys and memory states can be extracted.
  * **Stolen Root Cryptographic Secrets:** Compromising the `ATK_MASTER_ENCRYPTION_SECRET` allows an adversary to forge valid capability tokens and bypass signature gates.
  * **Malicious LLM Outputs:** ATK restricts system *actions and resource mutations*, not the underlying cognitive accuracy of semantic generations.
