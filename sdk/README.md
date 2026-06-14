# SEL v3 Python SDK

Zero-dependency sync client plus async production blueprint client.

## Sync Client

```python
from sel_v3 import SELClient, sel_guard

client = SELClient(
    gateway_url="http://127.0.0.1:8787",
    agent_id="autonomous_ops_worker",
    master_secret="your-master-secret",
)

@sel_guard(client, cost=0.05)
def execute_web_scrape(depth_limit: int, url: str) -> dict:
    return {"depth_limit": depth_limit, "url": url}
```

## Async Client

See `safe_runtime_v3.py` and `verify_system.py` for the production blueprint API with human-in-the-loop polling.
