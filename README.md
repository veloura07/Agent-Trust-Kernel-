# 🛡️ Agent Trust Kernel (ATK)

[![PyPI Version](https://img.shields.io/pypi/v/atk.svg)](https://pypi.org/project/atk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/yourorg/atk.svg?style=social)](https://github.com/yourorg/atk/stargazers)

### **The security and governance runtime wrapper for AI agents.**

The Agent Trust Kernel (ATK) is a local-first, high-performance security microkernel designed to insulate production tool environments from autonomous AI agent actions. It introduces an out-of-process control plane fence, separating an entity's fluid prompt behavior from deterministic system boundaries.

```text
       UNTRUSTED APPLICATION SPACE                 AGENT TRUST KERNEL RING (O(1))
 +---------------------------------------+        +----------------------------------+
 |  LangGraph / CrewAI Swarm Engine      |        |   Agent Trust Kernel Core Engine |
 |                                       |  Local |                                  |
 |  agent.send_email(to="unvetted.com")  |=======>|   * Token Authentication Check   |
 |  (Prone to indirect injections)       |  Call  |   * Compiled Policy Graph Match  |
 |                                       |        |   * Local Deterministic WAF Gate |
 +---------------------------------------+        +----------------------------------+
```

## ⚡ Quickstart (Under 30 Seconds)

### 1. Install via PyPI
```bash
pip install atk
```

### 2. Initialize the Policy Matrix
```bash
atk init
```
This deploys a declarative `atk.yaml` configuration directly into your current project workspace directory.

### 3. Wrap Your Autonomous Tools
```python
from atk import Agent

agent = Agent(name="autonomous_ops_worker")

@agent.guard(cost=0.005)
async def execute_web_scrape(url: str):
    return {"status": "success", "data": "Target content scraped safely."}
```

When called, the terminal prints real-time checking diagnostics directly to your console feed:
```text
✓ Permission Granted | Tool: execute_web_scrape | Tx: tx_8f2b3c4d5e6f | Cost Allocation: $0.005
Execution Successful | Action Receipt Proof Generated.
```

## 🗺️ Open-Source Feature Roadmap

* **v1.0.0 (Local Armor)**: Drop-in Python SDK decorator wrapping, O(1) compiled YAML policy graphs, cryptographic capability tokens, Write-Ahead Log (WAL) crash recovery journals, and append-only flat-file streams.
* **v2.0.0 (Behavioral DNA)**: Hierarchical behavior caching matrices tracking exploration tendencies, tool aggression vectors, and unsupervised behavioral drift anomaly alerts.
* **v3.0.0 (Explainability DAG)**: Full cause-and-effect lineage graphing capturing evidence nodes, decisions, and memory inputs to trace multi-agent swarm sub-delegations recursively.

## 🤝 Contributing
We welcome contributions to the Agent Trust Kernel! Please read our Contributing Guide and join our public Discord workspace.

## License
MIT
