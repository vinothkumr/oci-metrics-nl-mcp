from datetime import datetime, timezone
from typing import Any

import oci  # type: ignore[import-untyped]
from pydantic import BaseModel


def list_metric_names(
    monitoring: Any, compartment_id: str, namespace: str
) -> list[str]:
    items = oci.pagination.list_call_get_all_results(
        monitoring.list_metrics,
        compartment_id,
        oci.monitoring.models.ListMetricsDetails(
            namespace=namespace, group_by=["name"]
        ),
    ).data
    return sorted({item.name for item in items})


def list_metric_dimensions(
    monitoring: Any,
    compartment_id: str,
    namespace: str,
    metric_name: str,
) -> dict[str, list[str]]:
    items = oci.pagination.list_call_get_all_results(
        monitoring.list_metrics,
        compartment_id,
        oci.monitoring.models.ListMetricsDetails(namespace=namespace, name=metric_name),
    ).data
    dimensions: dict[str, set[str]] = {}
    for item in items:
        for key, value in (item.dimensions or {}).items():
            dimensions.setdefault(key, set()).add(value)
    return {key: sorted(values) for key, values in sorted(dimensions.items())}


class Datapoint(BaseModel):
    timestamp: str
    value: float


class MetricStream(BaseModel):
    name: str
    dimensions: dict[str, str]
    resolution: str | None
    point_count: int
    min_value: float | None
    max_value: float | None
    mean_value: float | None
    last_value: float | None
    first_timestamp: str | None
    last_timestamp: str | None
    datapoints: list[Datapoint] | None


class QueryResult(BaseModel):
    namespace: str
    query: str
    start_time: str
    end_time: str
    stream_count: int
    streams: list[MetricStream]


def _parse_iso(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _summarize_stream(md: Any, include_datapoints: bool) -> MetricStream:
    points = sorted(md.aggregated_datapoints or [], key=lambda p: p.timestamp)
    values = [p.value for p in points]
    count = len(values)
    return MetricStream(
        name=md.name,
        dimensions=md.dimensions or {},
        resolution=md.resolution,
        point_count=count,
        min_value=min(values) if values else None,
        max_value=max(values) if values else None,
        mean_value=sum(values) / count if count else None,
        last_value=values[-1] if values else None,
        first_timestamp=points[0].timestamp.isoformat() if points else None,
        last_timestamp=points[-1].timestamp.isoformat() if points else None,
        datapoints=(
            [
                Datapoint(timestamp=p.timestamp.isoformat(), value=p.value)
                for p in points
            ]
            if include_datapoints
            else None
        ),
    )


def query_metrics(
    monitoring: Any,
    compartment_id: str,
    namespace: str,
    query: str,
    start_time: str,
    end_time: str,
    resolution: str | None = None,
    include_datapoints: bool = False,
) -> QueryResult:
    start = _parse_iso(start_time)
    end = _parse_iso(end_time)
    if start >= end:
        raise ValueError("start_time must be before end_time")
    if end > datetime.now(timezone.utc):
        raise ValueError("end_time is in the future")
    if (end - start).days > 90:
        raise ValueError("time range exceeds 90 days, the maximum for any resolution")

    details = oci.monitoring.models.SummarizeMetricsDataDetails(
        namespace=namespace,
        query=query,
        start_time=start,
        end_time=end,
        resolution=resolution,
    )
    try:
        data = monitoring.summarize_metrics_data(compartment_id, details).data
    except Exception as exc:
        message = getattr(exc, "message", str(exc))
        raise RuntimeError(f"OCI rejected the query: {message}") from exc

    streams = [_summarize_stream(md, include_datapoints) for md in data]
    return QueryResult(
        namespace=namespace,
        query=query,
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        stream_count=len(streams),
        streams=streams,
    )
