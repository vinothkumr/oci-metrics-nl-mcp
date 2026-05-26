"""
Load OIC-shaped sample metrics into your OCI tenancy so you can try the server
without a live Oracle Integration instance.

It posts two fake integrations to a CUSTOM namespace ("mcp_validation"), mirroring
the real "oci_integration" metric/dimension shape:
  metrics    : BilledMessageCount (consumed/billable — the message-pack metric),
               MessagesSuccessfulCount
  dimensions : flowCode, flowVersion, integrationFlowIdentifier (combined "code!version"),
               resourceId (the OIC instance OCID)

  ORDERS-to-ERP!01.00.0000 : BilledMessageCount 10,20,...,100 (sum 550), Successful 10x10 (sum 100)
  CRM-Sync!02.00.0000      : BilledMessageCount 5x10 (sum 50),            Successful 5x10  (sum 50)

So `BilledMessageCount[1m].groupBy(integrationFlowIdentifier).sum()` ranks ORDERS-to-ERP
(550) above CRM-Sync (50) — the OIC "which integration burns the most message packs?" path.

WHY A CUSTOM NAMESPACE: OCI reserves the "oci_*" prefix (including "oci_integration")
for built-in service metrics — you cannot post to it. So sample data must use a custom
namespace; this script uses "mcp_validation". The metric and dimension NAMES match OIC;
only the namespace differs. Dimension VALUES (ORDERS-to-ERP, etc) are fake — against the
real oci_integration namespace they come from your actual integrations.

PERMISSIONS: the read-only server needs only `read metrics`. Posting needs METRIC_WRITE,
so to run THIS script add (temporarily) for your user's group:
    Allow group '<idcs>'/'<group>' to use metrics in tenancy
Drop back to `read metrics` afterwards.

Run from the project root:
    uv run python scripts/load_sample_data.py

Optional — post into a specific compartment instead of the root tenancy:
    OCI_VALIDATION_COMPARTMENT_OCID=ocid1.compartment.oc1..xxxx uv run python scripts/load_sample_data.py

Posted metrics take ~1-2 minutes to become queryable. The script prints the exact
namespace, time range, and MQL queries to paste into the MCP Inspector or ask Claude.
"""

import os
from datetime import datetime, timedelta, timezone

import oci

NAMESPACE = "mcp_validation"
RESOURCE_ID = "ocid1.integrationinstance.oc1.phx.fakeoic01"

profile = os.environ.get("OCI_PROFILE", "DEFAULT")
config = oci.config.from_file(profile_name=profile)
oci.config.validate_config(config)
if region := os.environ.get("OCI_REGION"):
    config["region"] = region

compartment_id = os.environ.get("OCI_VALIDATION_COMPARTMENT_OCID") or config["tenancy"]

# The default MonitoringClient points at the query endpoint (telemetry.<region>...).
# Posting requires the ingestion endpoint (telemetry-ingestion.<region>...).
query_client = oci.monitoring.MonitoringClient(config)
ingest_endpoint = query_client.base_client.endpoint.replace(
    "telemetry.", "telemetry-ingestion."
)
ingest_client = oci.monitoring.MonitoringClient(
    config, service_endpoint=ingest_endpoint
)
print(f"Ingestion endpoint : {ingest_endpoint}")
print(f"Compartment        : {compartment_id}")

now = datetime.now(timezone.utc).replace(second=0, microsecond=0)


def make_points(values: list[float]) -> list:
    n = len(values)
    return [
        oci.monitoring.models.Datapoint(
            timestamp=now - timedelta(minutes=(n - 1 - i)), value=float(v)
        )
        for i, v in enumerate(values)
    ]


integrations = [
    {
        "flow_code": "ORDERS-to-ERP",
        "flow_version": "01.00.0000",
        "BilledMessageCount": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "MessagesSuccessfulCount": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    },
    {
        "flow_code": "CRM-Sync",
        "flow_version": "02.00.0000",
        "BilledMessageCount": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
        "MessagesSuccessfulCount": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
    },
]

metric_data = []
for integ in integrations:
    flow_code = integ["flow_code"]
    flow_version = integ["flow_version"]
    dimensions = {
        "flowCode": flow_code,
        "flowVersion": flow_version,
        "integrationFlowIdentifier": f"{flow_code}!{flow_version}",
        "resourceId": RESOURCE_ID,
    }
    for metric_name in ("BilledMessageCount", "MessagesSuccessfulCount"):
        metric_data.append(
            oci.monitoring.models.MetricDataDetails(
                namespace=NAMESPACE,
                compartment_id=compartment_id,
                name=metric_name,
                dimensions=dimensions,
                datapoints=make_points(integ[metric_name]),
            )
        )

details = oci.monitoring.models.PostMetricDataDetails(metric_data=metric_data)
resp = ingest_client.post_metric_data(details)
print(
    f"\nPosted {len(metric_data)} streams. "
    f"failed_metrics_count = {resp.data.failed_metrics_count}"
)
if resp.data.failed_metrics_count:
    print("FAILED:", resp.data.failed_metrics)

start = (now - timedelta(minutes=12)).isoformat().replace("+00:00", "Z")
end = (now + timedelta(minutes=2)).isoformat().replace("+00:00", "Z")

print("\n--- Try it (wait ~1-2 min for ingestion) ---")
print(f"namespace   : {NAMESPACE}")
print(f"compartment : {compartment_id}")
print(f"start_time  : {start}")
print(f"end_time    : {end}")
print()
print("Query 1 — per-integration billed total (the headline path):")
print("  BilledMessageCount[1m].groupBy(integrationFlowIdentifier).sum()")
print("  expect: ORDERS-to-ERP!01.00.0000 = 550, CRM-Sync!02.00.0000 = 50")
print()
print("Query 2 — dimension filter:")
print('  BilledMessageCount[1m]{flowCode = "ORDERS-to-ERP"}.sum()  -> 550')
print()
print("Query 3 — second metric sanity:")
print("  MessagesSuccessfulCount[1m].groupBy(integrationFlowIdentifier).sum()")
print("  expect: ORDERS-to-ERP!01.00.0000 = 100, CRM-Sync!02.00.0000 = 50")
