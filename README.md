# oci-metrics-nl-mcp

**Work in progress**
 
**Ask your OCI metrics in English. Get answers, not dashboards.**
 
An MCP server that lets Claude, ChatGPT, Cursor, and any other MCP-compatible client query Oracle Cloud Infrastructure Monitoring metrics through natural language. Built first for Oracle Integration Cloud (OIC) — because *"which integration is burning through our message packs?"* is the question Metrics Explorer cannot answer in fewer than six clicks.
 
```
You:    Which integrations consumed the most message packs last week?
Claude: SAP-to-Salesforce is your biggest consumer at 4.2M packs (38% of total),
        followed by Workday-Sync at 2.1M. SAP-to-Salesforce is also up 67% week-
        over-week — most of the increase came Tuesday afternoon. Want me to
        propose an alarm for next time it crosses 3M in a rolling 24h window?
 
You:    Yes, set that up.
Claude: [proposes alarm payload]
You:    Confirmed.
Claude: ✓ Alarm "SAP-Salesforce message pack spike" created in compartment X.
```
 
> ⚠️ Not affiliated with Oracle Corporation. Built independently using the public OCI SDK and Monitoring APIs.

> Built by me, with Claude Code as a coding pair. Architecture, design decisions, and review by me; implementation accelerated by AI.
 
---

## Quick start

### Prerequisites

- Python 3.11–3.13
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An OCI account with `~/.oci/config` set up ([OCI SDK config guide](https://docs.oracle.com/iaas/tools/python/latest/sdk_behaviors/config.html))

### Install

```bash
git clone https://github.com/vinothkumr/oci-metrics-nl-mcp.git
cd oci-metrics-nl-mcp
uv sync
```

### Claude Desktop config

Open `~/Library/Application Support/Claude/claude_desktop_config.json` and add the server under `mcpServers`:

```json
{
  "mcpServers": {
    "oci-metrics-nl-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/oci-metrics-nl-mcp",
        "run",
        "oci-metrics-nl-mcp"
      ]
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/oci-metrics-nl-mcp` with the actual path on your machine (e.g. `/Users/yourname/Downloads/claude-workspace/oci-metrics-nl-mcp`).

The tenancy OCID is read automatically from the `tenancy` field in `~/.oci/config`. No extra env vars needed for a standard setup.

Restart Claude Desktop. Ask:

> What can I query in OCI right now?

Claude will call `list_observable_resources` and return your compartments and active metric namespaces.

### Optional env vars

| Variable | Default | Purpose |
|---|---|---|
| `OCI_TENANCY_OCID` | from `~/.oci/config` | Override the tenancy OCID |
| `OCI_PROFILE` | `DEFAULT` | Profile name in `~/.oci/config` |
| `OCI_REGION` | from config | Override the region |

---