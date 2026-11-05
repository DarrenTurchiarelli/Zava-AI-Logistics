"""Read-only, bounded Cosmos projections for the demand planner."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from functools import lru_cache
from threading import Lock
from time import monotonic
from typing import Any

from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient
from azure.cosmos.database import DatabaseProxy
from azure.identity import AzureCliCredential, ManagedIdentityCredential

from parcel_tracking_db import ParcelTrackingDB
from src.domain.services.planning_operations import (
    PlanningFeed,
    PlanningOperations,
    latest_record_update,
    reconcile_operations,
)

logger = logging.getLogger(__name__)
_LIMIT = 20000
_cache_lock = Lock()
_PlanningRecords = dict[str, list[dict[str, Any]] | None]
_SourceSnapshot = tuple[_PlanningRecords, tuple[PlanningFeed, ...], datetime]
_cached_snapshot: _SourceSnapshot | None = None
_cache_expires = 0.0
_QUERIES = {
    "parcels": (
        "parcels",
        "c.id, c.barcode, c.tracking_number, c.current_status, c.current_location, "
        "c.requires_approval, c.approval_status, c.is_delivered, c._ts",
        "",
    ),
    "approvals": (
        "delivery_attempts",
        "c.id, c.parcel_barcode, c.barcode, c.tracking_number, c.parcel_id, "
        "c.status, c.request_type, c._ts",
        " WHERE IS_DEFINED(c.request_type)",
    ),
    "manifests": (
        "driver_manifests",
        'c.id, c.driver_id, c.manifest_date, c.status, c._ts, '
        'ARRAY(SELECT VALUE {"barcode": i.barcode, "tracking_number": i.tracking_number, '
        '"status": i.status} FROM i IN c.items) AS items',
        "",
    ),
    "drivers": (
        "users",
        "c.id, c.state, c.active, c._ts",
        " WHERE c.role = 'driver'",
    ),
}


@lru_cache(maxsize=1)
def _planning_database() -> DatabaseProxy:
    config = ParcelTrackingDB()
    if not config.endpoint:
        raise ValueError("COSMOS_DB_ENDPOINT or COSMOS_CONNECTION_STRING is required.")
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        credential = ManagedIdentityCredential()
    else:
        credential = config.key or AzureCliCredential(process_timeout=60)
    # Do not use ParcelTrackingDB.connect(): key-auth connections can create resources.
    client = CosmosClient(config.endpoint, credential=credential, connection_timeout=10, timeout=30)
    return client.get_database_client(config.database_name)


def _read_feed(
    database: DatabaseProxy, name: str, fetched_at: datetime,
) -> tuple[list[dict[str, Any]] | None, PlanningFeed]:
    container_name, projection, where = _QUERIES[name]
    try:
        container = database.get_container_client(container_name)
        items = list(container.query_items(
            query=f"SELECT TOP {_LIMIT + 1} {projection} FROM c{where}",
            enable_cross_partition_query=True, max_item_count=500,
        ))
        if len(items) > _LIMIT:
            logger.error("Demand planner %s feed exceeds the %s-record safety limit", name, _LIMIT)
            return None, PlanningFeed(
                name, False, fetched_at, issue=f"{name}: safety limit exceeded; partial totals are not used.",
            )
        return items, PlanningFeed(
            name, True, fetched_at, records=len(items), latest_update=latest_record_update(items),
        )
    except AzureError:
        logger.exception("Demand planner %s read failed", name)
        return None, PlanningFeed(
            name, False, fetched_at, issue=f"{name}: read failed; this feed is unavailable, not empty.",
        )


def _read_source_snapshot() -> _SourceSnapshot:
    fetched_at = datetime.now(UTC)
    records: dict[str, list[dict[str, Any]] | None] = {}
    feeds = []
    try:
        database = _planning_database()
    except (AzureError, ValueError):
        logger.exception("Demand planner operational connection is unavailable")
        for name in _QUERIES:
            records[name] = None
            feeds.append(PlanningFeed(name, False, fetched_at, issue=f"{name}: application feed unavailable."))
    else:
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = executor.map(lambda name: _read_feed(database, name, fetched_at), _QUERIES)
            for name, (items, feed) in zip(_QUERIES, results, strict=True):
                records[name] = items
                feeds.append(feed)
    return records, tuple(feeds), fetched_at


def read_planning_operations(facility_code: str, local_day: str, *, refresh: bool = False) -> PlanningOperations:
    global _cached_snapshot, _cache_expires
    with _cache_lock:
        if refresh or _cached_snapshot is None or monotonic() >= _cache_expires:
            _cached_snapshot = _read_source_snapshot()
            _cache_expires = monotonic() + (30 if all(feed.available for feed in _cached_snapshot[1]) else 5)
        records, feeds, fetched_at = _cached_snapshot
    return reconcile_operations(facility_code, local_day, records, feeds, fetched_at)
