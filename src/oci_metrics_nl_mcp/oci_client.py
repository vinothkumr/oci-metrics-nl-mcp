import logging
import os
from dataclasses import dataclass
from typing import Any

import oci  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def _load_config() -> dict:
    profile = os.environ.get("OCI_PROFILE", "DEFAULT")
    config = oci.config.from_file(profile_name=profile)
    oci.config.validate_config(config)
    if region := os.environ.get("OCI_REGION"):
        config["region"] = region
    return config


@dataclass
class OciClients:
    identity: Any
    monitoring: Any
    tenancy_ocid: str


def build_clients() -> OciClients:
    config = _load_config()
    tenancy_ocid = os.environ.get("OCI_TENANCY_OCID") or config["tenancy"]
    return OciClients(
        identity=oci.identity.IdentityClient(config),
        monitoring=oci.monitoring.MonitoringClient(config),
        tenancy_ocid=tenancy_ocid,
    )
