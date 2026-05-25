import asyncio

from oci_metrics_nl_mcp.server import mcp


def test_list_observable_resources_is_registered():
    tools = asyncio.run(mcp.list_tools())
    names = [t.name for t in tools]
    assert "list_observable_resources" in names
