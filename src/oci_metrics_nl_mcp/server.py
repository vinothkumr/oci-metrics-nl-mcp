import logging
import sys
import warnings
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import oci  # type: ignore[import-untyped]
from fastmcp import FastMCP
from pydantic import BaseModel

from oci_metrics_nl_mcp.oci_client import OciClients, build_clients

logger = logging.getLogger(__name__)

_clients: OciClients | None = None


@asynccontextmanager
async def _lifespan(server: Any) -> AsyncIterator[None]:
    global _clients
    warnings.filterwarnings(
        "ignore",
        message="The 'strict' parameter is no longer needed",
        category=FutureWarning,
    )
    _clients = build_clients()
    yield


mcp = FastMCP("oci-metrics-nl-mcp", lifespan=_lifespan)


class CompartmentResources(BaseModel):
    id: str
    name: str
    namespaces: list[str]


class ObservableResources(BaseModel):
    compartments: list[CompartmentResources]


@dataclass
class _CompartmentRef:
    id: str
    name: str


@mcp.tool()
def list_observable_resources() -> ObservableResources:
    """Return all accessible compartments and the metric namespaces active in each.

    Use this before querying metrics — it shows what data is available in your OCI
    tenancy right now.

    Example response:
        {
          "compartments": [
            {"id": "ocid1.compartment...", "name": "PersonalDB",
             "namespaces": ["oci_computeagent", "oci_blockstore"]}
          ]
        }
    """
    assert _clients is not None

    raw = oci.pagination.list_call_get_all_results(
        _clients.identity.list_compartments,
        _clients.tenancy_ocid,
        compartment_id_in_subtree=True,
        lifecycle_state="ACTIVE",
    ).data

    compartments = [_CompartmentRef(id=_clients.tenancy_ocid, name="(root tenancy)")]
    compartments += [_CompartmentRef(id=c.id, name=c.name) for c in raw]

    return ObservableResources(
        compartments=[
            CompartmentResources(
                id=c.id,
                name=c.name,
                namespaces=_list_namespaces(c.id, c.name),
            )
            for c in compartments
        ]
    )


def _list_namespaces(compartment_id: str, compartment_name: str) -> list[str]:
    assert _clients is not None
    try:
        items = oci.pagination.list_call_get_all_results(
            _clients.monitoring.list_metrics,
            compartment_id,
            oci.monitoring.models.ListMetricsDetails(group_by=["namespace"]),
        ).data
        return sorted({item.namespace for item in items})
    except Exception as exc:
        status = getattr(exc, "status", None)
        if status in (401, 403, 404):
            logger.warning("Cannot list metrics for %s: HTTP %s", compartment_name, status)
            return []
        raise


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
    mcp.run()


if __name__ == "__main__":
    main()
