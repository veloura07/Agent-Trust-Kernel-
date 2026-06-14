# 🛡️ AgentGuard

[![PyPI Version](https://img.shields.io/pypi/v/agentguard.svg)](https://pypi.org/project/agentguard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/yourorg/agentguard/workflows/CI/badge.svg)](https://github.com/yourorg/agentguard/actions)
[![GitHub Stars](https://img.shields.io/github/stars/yourorg/agentguard.svg)](https://github.com/yourorg/agentguard/stargazers)

### **The security and governance runtime wrapper for AI agents.**

AgentGuard is a local-first, zero-dependency proxy and security microkernel designed to insulate software tool spaces from autonomous AI agent actions. It acts as an out-of-process control plane fence, completely separating an entity's fluid prompt logic from deterministic system governance.

```text
       UNTRUSTED APPLICATION SPACE                 AGENTGUARD FIREWALL RING (O(1))
 +---------------------------------------+        +----------------------------------+
 |  LangGraph / CrewAI Swarm Engine      |        |   AgentGuard Deterministic Core  |
 |                                       |  Local |                                  |
 |  agent.send_email(to="unvetted.com")  |=======>|   * Token Authentication Check   |
 |  (Prone to indirect injections)       |  Call  |   * Compiled Policy Graph Match  |
 |                                       |        |   * Local Deterministic WAF Gate |
 +---------------------------------------+        +----------------------------------+
```

## ⚡ Quickstart (Under 30 Seconds)

### 1. Install via PyPI
```bash
pip install agentguard
```

### 2. Initialize the Policy Matrix
```bash
agentguard init
```
This maps a declarative `agentguard.yaml` contract directly into your local workspace.

### 3. Wrap Your Autonomous Tools
```python
from agentguard import Agent

agent = Agent(name="autonomous_ops_worker")

@agent.guard(cost=0.005)
async def execute_web_scrape(url: str):
    # Your raw tool execution logic lives safely here
    return {"status": "success", "data": "Pristine context."}
```

When called, the terminal streams high-speed checking diagnostics directly to your stdout console layout feed:
```text
✓ Permission Granted | Tool: execute_web_scrape | Tx: tx_8f2b3c4d5e6f | Cost Allocation: $0.005
Execution Successful | Action Receipt Proof Generated.
```

## 🗺️ Open-Source Feature Roadmap

* **v1.0.0 (Local Armor)**: Drop-in Python SDK decorator wrapping, $O(1)$ compiled YAML policy graphs, cryptographic capability tokens, append-only flat-file streams, and the embedded terminal dashboard monitor.
* **v2.0.0 (Behavioral DNA)**: Hierarchical behavior caching matrices tracking exploration tendencies, tool aggression vectors, and unsupervised K-Means behavioral drift anomaly alerts.
* **v3.0.0 (Explainability DAG)**: Full cause-and-effect lineage graphing capturing evidence nodes, decisions, and memory inputs to trace multi-agent swarm sub-delegations recursively.
* **v4.0.0 (The Time Machine)**: Local state replay engines reconstructing execution context prompts, snapshots, and vector adjustments at any chronological timestamp slice.

## 🤝 Contributing
We welcome contributions to AgentGuard! Please read our Contributing Guide and join the discussion inside our public Discord channel workspace.

## License
MIT
