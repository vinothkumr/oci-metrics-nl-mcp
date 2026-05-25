# CLAUDE.md

Project memory for Claude Code. Read in full at session start.

---

## How we work together — the rules of this project

**This is a learning project for the user. Pace matters more than speed.**

- The user reviews every change before commit. Show diffs. Explain reasoning. Wait for confirmation.
- **For every Python file you create or significantly change, produce a sibling HTML file** that explains it line by line. `src/foo/bar.py` gets `src/foo/bar.html`. Format below.
- **Stop after each step in the plan.** Do not run ahead. After a step is reviewed and committed by the user, wait for them to say "proceed to step N+1."
- Opus advisor is enabled (the user already ran `/advisor`). Defer hard decisions or any ambiguity to advisor mode. Don't guess.
- No mocks, no fakes, no synthetic data in v0.1. The tool talks to the user's real OCI tenancy. They want to see real results.

---

## v0.1 scope — exactly one tool

A single MCP tool: **`list_observable_resources`**.

What it does: returns the compartments the user has access to, and for each compartment, the metric namespaces that have data in them. Answers "what can I query in OCI right now?" — a discovery tool.

Return shape (proposed; finalize during step 3):
```json
{
  "compartments": [
    {
      "id": "ocid1.compartment.oc1..xxx",
      "name": "myproject",
      "namespaces": ["oci_computeagent", "oci_lbaas"]
    }
  ]
}
```

**Everything else is v0.2 or later.** No `find_top_consumers`, no propose/confirm, no synthetic data generator, no alarms, no CI/CD. Don't add scaffolding for them.

---

## Tech stack — exact versions

| Component | Version |
|---|---|
| Python | `>=3.11,<3.14` (recommend 3.12) |
| uv | latest (already installed) |
| fastmcp | `>=3.3` |
| oci | `>=2.140,<3.0` |
| pydantic | `>=2.0,<3.0` |
| pytest | `>=8.0` |
| ruff | `>=0.6` |
| pyright | `>=1.1.380` |

Add deps with `uv add <pkg>` — never edit `pyproject.toml` by hand.

---

## OCI auth

- Reads `~/.oci/config`, profile `DEFAULT`.
- Required env var at server startup: `OCI_TENANCY_OCID` — the root tenancy OCID. Without it, fail fast with a clear stderr message. (We use this as the starting compartment for the recursive `list_compartments` walk.)
- Optional: `OCI_PROFILE` overrides the profile name. `OCI_REGION` overrides the region.

---

## Coding conventions

- Python 3.11+ syntax. `list[str]`, `X | None`, no `from typing import List/Optional`.
- Type hints everywhere. `uv run pyright src/` clean.
- Format with `uv run ruff format .`.
- Log to stderr via `logging` module. Never `print()`.
- One module = one clear purpose. No god-files.

---

## The HTML explainer — required for every Python file

When you create or significantly change `src/path/file.py`, also write `src/path/file.html`.

Use this template (clean, no JS, opens in any browser):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>file.py — explained</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; max-width: 900px;
           margin: 2em auto; padding: 0 1em; line-height: 1.6; color: #1a1a1a; }
    h1, h2 { border-bottom: 1px solid #eaeaea; padding-bottom: 0.3em; }
    h2 { margin-top: 2em; }
    pre { background: #f6f8fa; padding: 1em; border-radius: 6px;
          overflow-x: auto; font-size: 0.9em; }
    code { font-family: 'SF Mono', Menlo, Consolas, monospace; }
    .why { background: #fffbeb; border-left: 3px solid #f59e0b;
           padding: 0.6em 1em; margin: 0.5em 0 1.5em; border-radius: 0 4px 4px 0; }
    .why strong { color: #92400e; }
    nav { background: #f0f9ff; padding: 0.8em 1em; border-radius: 6px;
          margin-bottom: 2em; font-size: 0.95em; }
  </style>
</head>
<body>
  <h1>file.py — line by line</h1>
  <nav>
    <strong>What this file does:</strong> [one or two sentences]<br>
    <strong>How it fits in the project:</strong> [one sentence]
  </nav>

  <h2>1. [Section name, e.g. "Imports"]</h2>
  <pre><code>[the actual code from this section]</code></pre>
  <div class="why">
    <strong>What's happening:</strong> [explain what the code does]<br>
    <strong>Why this way:</strong> [explain why this approach vs alternatives]
  </div>

  <!-- repeat sections for each logical chunk of the file -->

  <h2>If you want to dig deeper</h2>
  <ul>
    <li>[link to relevant docs]</li>
  </ul>
</body>
</html>
```

The HTML is for the user's learning. Write it like you're teaching, not documenting. Mention *why* a choice was made, what alternatives exist, what gotchas to know.

---

## The plan — five steps for v0.1

Execute one at a time. **Stop after each. Wait for "proceed."**

### Step 1 — Project skeleton
**Make:**
- `pyproject.toml` (uv-managed, package name `oci-metrics-nl-mcp`, entry point `oci-metrics-nl-mcp = "oci_metrics_nl_mcp.server:main"`)
- `.python-version` pinning 3.12
- `.gitignore` (Python + uv + OS)
- `src/oci_metrics_nl_mcp/__init__.py` (one line exporting `__version__`)
- `src/oci_metrics_nl_mcp/server.py` (FastMCP instance + `main()` function, **no tools yet**)
- HTML explainers: `__init__.html`, `server.html`

**Done when:**
- `uv sync` runs clean
- `uv run fastmcp dev inspector src/oci_metrics_nl_mcp/server.py` starts the inspector
- User reviews diffs, opens HTML files, confirms they make sense
- Then STOP

### Step 2 — OCI client wrapper
**Make:**
- `src/oci_metrics_nl_mcp/oci_client.py` — loads `~/.oci/config`, creates `IdentityClient` and `MonitoringClient`, exposes typed accessors
- `oci_client.html` explainer
- Add `oci` to `pyproject.toml` deps via `uv add oci`

**Done when:**
- A tiny ad-hoc script (in scratch, not committed) imports the client and successfully calls `list_compartments` against the user's real tenancy
- User confirms the call returns their actual compartments
- HTML reviewed
- Then STOP

### Step 3 — The tool
**Make:**
- Add `list_observable_resources` tool to `server.py`
  - For each compartment: call `MonitoringClient.list_metrics`, extract unique namespaces
  - Returns the structured shape shown in v0.1 scope above
- Update `server.html` to cover the new code
- Pydantic model for the response

**Done when:**
- MCP Inspector calls the tool against user's real tenancy
- User sees their real compartments + real namespaces in the response
- HTML reviewed
- Then STOP

### Step 4 — Smoke test
**Make:**
- `tests/test_smoke.py` — one test that imports the server module and verifies the tool is registered. No OCI calls.
- `pyproject.toml` adds `pytest` to dev deps via `uv add --dev pytest`

**Done when:**
- `uv run pytest` passes
- User reviews
- Then STOP

### Step 5 — End-to-end check with Claude Desktop
**Make:**
- Append to `README.md` (or create it if missing): "Quick start" with the Claude Desktop config snippet
- No code changes

**Done when:**
- User adds the MCP server to their Claude Desktop config, restarts Claude, asks "what can I query in OCI?", and the tool returns real data
- This is v0.1 shipped. The user manually publishes to PyPI (or just leaves it as a GitHub repo) at their pace.

---

## When you're unsure

Use Opus advisor. Five triggers:
1. This file doesn't unambiguously resolve a question.
2. You're about to invent a name, pattern, or convention.
3. The user's prompt conflicts with this file.
4. You're about to skip a "done when" item.
5. You're tempted to do step N+1 work inside step N.

Surface the question to the user. Decide together. If permanent, edit this file.

---

## Deferred to v0.2 (don't build now)

- Synthetic data generator + personas
- Intent tools (`find_top_consumers`, `compare_periods`, `explain_anomaly`)
- Write tools + propose/confirm pattern
- Alarms
- `run_mql_query` escape hatch
- GitHub Actions CI / release workflows
- Multi-Python-version testing

These have designs already (see git history of this file if curious), but they're out of scope for v0.1.

---

## References

- MCP: https://modelcontextprotocol.io/docs
- FastMCP: https://github.com/jlowin/fastmcp
- OCI Python SDK: https://docs.oracle.com/iaas/tools/python/latest/
- OCI Monitoring: https://docs.oracle.com/iaas/api/#/en/monitoring/
- Reference MCP server: https://github.com/oracle/mcp/tree/main/src/oci-compute-mcp-server