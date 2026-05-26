import asyncio

from oci_metrics_nl_mcp.server import mcp

EXPECTED_TOOLS = {
    "list_observable_resources",
    "list_metric_names",
    "list_metric_dimensions",
    "query_metrics",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert EXPECTED_TOOLS <= names
