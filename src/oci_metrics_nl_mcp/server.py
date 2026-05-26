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

from oci_metrics_nl_mcp import oci_metrics
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


class MetricNames(BaseModel):
    namespace: str
    names: list[str]


class MetricDimensions(BaseModel):
    namespace: str
    metric_name: str
    dimensions: dict[str, list[str]]


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
            logger.warning(
                "Cannot list metrics for %s: HTTP %s", compartment_name, status
            )
            return []
        raise


@mcp.tool()
def list_metric_names(compartment_id: str, namespace: str) -> MetricNames:
    """List the metric names available in a namespace within a compartment.

    Call this after list_observable_resources to drill from a namespace into its
    specific metrics — e.g. namespace "oci_computeagent" contains "CpuUtilization",
    "MemoryUtilization". Pass the compartment id and namespace exactly as returned
    by list_observable_resources.
    """
    assert _clients is not None
    return MetricNames(
        namespace=namespace,
        names=oci_metrics.list_metric_names(
            _clients.monitoring, compartment_id, namespace
        ),
    )


@mcp.tool()
def list_metric_dimensions(
    compartment_id: str, namespace: str, metric_name: str
) -> MetricDimensions:
    """List the dimension keys and their observed values for one metric.

    Dimensions are the attributes you can filter or group by — e.g. "resourceId",
    "availabilityDomain", or "integrationId". Use this to discover valid groupBy
    targets and filter values before writing an MQL query for query_metrics.
    """
    assert _clients is not None
    return MetricDimensions(
        namespace=namespace,
        metric_name=metric_name,
        dimensions=oci_metrics.list_metric_dimensions(
            _clients.monitoring, compartment_id, namespace, metric_name
        ),
    )


@mcp.tool()
def query_metrics(
    compartment_id: str,
    namespace: str,
    query: str,
    start_time: str,
    end_time: str,
    resolution: str | None = None,
    include_datapoints: bool = False,
) -> oci_metrics.QueryResult:
    """Run an MQL query against OCI Monitoring and return summarized time series.

    `query` is a raw Monitoring Query Language (MQL) string of the form
    `MetricName[interval].statistic()` — e.g. "CpuUtilization[1h].mean()" or
    "MessagesReceived[1h].sum()". Add a dimension filter with
    `{key = "value"}` and split by a dimension with `.groupBy(key)` —
    e.g. `MessagesReceived[1h]{}.groupBy(integrationId).sum()` to break OIC
    message volume out per integration.

    Discover valid metric names with list_metric_names and valid dimension
    keys/values with list_metric_dimensions first.

    `start_time` and `end_time` are ISO-8601 UTC strings (e.g.
    "2026-05-19T00:00:00Z"). `resolution` (e.g. "1h") is optional; OCI infers
    it from the query interval when omitted.

    By default each stream is summarized (min/max/mean/last/count) to keep the
    response small. Set include_datapoints=True to also get every raw datapoint
    — but narrow the query with dimension filters first, since a large groupBy
    plus raw datapoints can exceed context limits.
    """
    assert _clients is not None
    return oci_metrics.query_metrics(
        _clients.monitoring,
        compartment_id,
        namespace,
        query,
        start_time,
        end_time,
        resolution,
        include_datapoints,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )
    mcp.run()


if __name__ == "__main__":
    main()
