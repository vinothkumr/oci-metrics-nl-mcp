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
 
---