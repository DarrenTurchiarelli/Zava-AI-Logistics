"""
Azure AI Agent Tools for Cosmos DB Integration
Provides tools for agents to query Cosmos DB directly for real-time data.

IMPORTANT: These functions are SYNCHRONOUS — they are executed inside a
ThreadPoolExecutor by base.py and must not be async.  Using the sync
Cosmos SDK avoids all event-loop/aiohttp credential issues that arise
when async code runs inside a throwaway event loop on a worker thread.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from azure.cosmos import CosmosClient, exceptions as cosmos_exceptions
from azure.identity import AzureCliCredential, ManagedIdentityCredential
from dotenv import load_dotenv

load_dotenv()


def _get_cosmos_container(container_name: str):
    """Return a sync ContainerClient.  Creates a fresh credential every call
    so there is no shared state between tool invocations."""
    load_dotenv(override=True)
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logisticstracking")

    if not endpoint:
        raise ValueError("COSMOS_DB_ENDPOINT not set")

    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        credential = ManagedIdentityCredential()
    else:
        credential = AzureCliCredential(process_timeout=60)

    client = CosmosClient(endpoint, credential)
    db = client.get_database_client(database_name)
    return db.get_container_client(container_name)


def track_parcel_tool(tracking_number: str) -> str:
    """
    Tool for AI agents to track a parcel in real-time from Cosmos DB.

    Args:
        tracking_number: The parcel tracking number to look up

    Returns:
        JSON string with parcel status, location, and tracking history
    """
    print(f"🔧 Agent Tool: track_parcel_tool called with tracking_number={tracking_number}")

    try:
        container = _get_cosmos_container("parcels")

        parcels = list(container.query_items(
            query="""SELECT * FROM c
                     WHERE c.tracking_number = @id1
                     OR c.barcode = @id2
                     OR c.id = @id3""",
            parameters=[
                {"name": "@id1", "value": tracking_number},
                {"name": "@id2", "value": tracking_number},
                {"name": "@id3", "value": tracking_number},
            ],
            enable_cross_partition_query=True,
        ))

        if not parcels:
            print(f"   ❌ Parcel not found with identifier: {tracking_number}")
            return json.dumps({
                "found": False,
                "message": f"No parcel found with identifier {tracking_number}",
                "tracking_number": tracking_number,
            })

        parcel = parcels[0]

        # Get tracking events
        ev_container = _get_cosmos_container("tracking_events")
        events = list(ev_container.query_items(
            query="""SELECT * FROM c
                     WHERE c.barcode = @id1
                     OR c.tracking_number = @id2
                     OR c.id = @id3
                     ORDER BY c.timestamp DESC""",
            parameters=[
                {"name": "@id1", "value": parcel.get("barcode", tracking_number)},
                {"name": "@id2", "value": tracking_number},
                {"name": "@id3", "value": tracking_number},
            ],
            enable_cross_partition_query=True,
        ))

        # Build response
        result = {
            "found": True,
            "tracking_number": parcel.get("tracking_number"),
            "barcode": parcel.get("barcode"),
            "status": parcel.get("current_status") or parcel.get("status"),
            "current_location": parcel.get("current_location"),
            "destination": parcel.get("destination") or f"{parcel.get('destination_city', '')} {parcel.get('destination_state', '')}".strip() or None,
            "estimated_delivery": parcel.get("estimated_delivery"),
            "service_type": parcel.get("service_type"),
            "created_at": parcel.get("created_at") or parcel.get("registration_timestamp"),
            "sender_name": parcel.get("sender_name") or (parcel.get("sender", {}) or {}).get("name"),
            "sender_address": parcel.get("sender_address") or (parcel.get("sender", {}) or {}).get("address"),
            "recipient_name": parcel.get("recipient_name") or (parcel.get("recipient", {}) or {}).get("name"),
            "recipient_address": parcel.get("recipient_address") or (parcel.get("recipient", {}) or {}).get("address"),
            "recipient_postcode": parcel.get("destination_postcode") or parcel.get("recipient_postcode") or (parcel.get("recipient", {}) or {}).get("postcode"),
            "delivery_photos": [
                {
                    "uploaded_by": photo.get("uploaded_by"),
                    "timestamp": photo.get("timestamp"),
                    "photo_size_kb": photo.get("photo_size_kb") or (len(photo.get("photo_data", "")) // 1024),
                    # photo_data excluded — base64 content is fetched directly by the UI,
                    # not passed through the LLM (avoids 10K–100K token tool responses)
                    "has_photo": bool(photo.get("photo_data")),
                }
                for photo in parcel.get("delivery_photos", [])
            ],
            "delivery_photos_count": len(parcel.get("delivery_photos", [])),
            "lodgement_photos": [
                {
                    "uploaded_by": photo.get("uploaded_by"),
                    "timestamp": photo.get("timestamp"),
                    "photo_size_kb": photo.get("photo_size_kb") or (len(photo.get("photo_data", "")) // 1024),
                    "has_photo": bool(photo.get("photo_data")),
                }
                for photo in parcel.get("lodgement_photos", [])
            ],
            "lodgement_photos_count": len(parcel.get("lodgement_photos", [])),
            "recent_events": [
                {
                    "timestamp": e.get("timestamp"),
                    "status": e.get("status"),
                    "location": e.get("location"),
                    "description": e.get("description"),
                }
                for e in (events[:5] if events else [])
            ],
            "total_events": len(events) if events else 0,
        }

        print(f"   ✅ Found parcel - Sender: {result['sender_name']}, Recipient: {result['recipient_name']}, Status: {result['status']}")
        return json.dumps(result, indent=2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({
            "found": False,
            "lookup_error": True,
            "error": str(e),
            "tracking_number": tracking_number,
            "message": "A system error occurred while looking up this parcel. Please try again.",
        })


def search_parcels_by_recipient_tool(
    recipient_name: str = None, postcode: str = None, address: str = None, days_back: int = None
) -> str:
    """
    Tool for AI agents to search parcels by recipient name, postcode, or address with optional date filtering.

    Args:
        recipient_name: Recipient name to search for (optional)
        postcode: Postcode to search for (optional)
        address: Full or partial address to search for (optional)
        days_back: Number of days to look back from today (e.g., 21 for last 3 weeks, 7 for last week)

    Returns:
        JSON string with list of matching parcels including barcode and created_at
    """
    print(
        f"🔧 Agent Tool: search_parcels_by_recipient_tool called - name={recipient_name}, postcode={postcode}, address={address}, days_back={days_back}"
    )

    try:
        container = _get_cosmos_container("parcels")
        query_parts = []
        parameters = []

        if recipient_name:
            query_parts.append("CONTAINS(LOWER(c.recipient_name), @recipient_name)")
            parameters.append({"name": "@recipient_name", "value": recipient_name.lower()})
        if postcode:
            query_parts.append("(c.destination_postcode = @postcode OR c.recipient_postcode = @postcode OR CONTAINS(c.recipient_address, @postcode))")
            parameters.append({"name": "@postcode", "value": postcode})
        if address:
            query_parts.append("CONTAINS(LOWER(c.recipient_address), @address)")
            parameters.append({"name": "@address", "value": address.lower()})
        if days_back:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            query_parts.append("c.created_at >= @cutoff_date")
            parameters.append({"name": "@cutoff_date", "value": cutoff})

        if not query_parts:
            return json.dumps({"found": False, "count": 0, "parcels": [], "error": "No search criteria provided"})

        query = f"SELECT * FROM c WHERE {' AND '.join(query_parts)} ORDER BY c.created_at DESC"
        parcels = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))[:20]

        print(f"   ✅ Found {len(parcels)} parcels matching search criteria")
        return json.dumps({"found": len(parcels) > 0, "count": len(parcels), "parcels": parcels,
                           "search_criteria": {"recipient_name": recipient_name, "postcode": postcode,
                                               "address": address, "days_back": days_back}}, indent=2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"found": False, "error": str(e)})


def search_parcels_by_driver_tool(driver_id: str = None, driver_name: str = None, status: str = None) -> str:
    """
    Tool for AI agents to search parcels assigned to a specific driver.

    Args:
        driver_id: Driver ID (e.g., 'driver-001') - optional
        driver_name: Driver name to search for (optional)
        status: Parcel status filter (e.g., 'in_transit', 'out_for_delivery') - optional

    Returns:
        JSON string with list of parcels assigned to the driver
    """
    print(
        f"🔧 Agent Tool: search_parcels_by_driver_tool called - driver_id={driver_id}, driver_name={driver_name}, status={status}"
    )

    try:
        container = _get_cosmos_container("parcels")
        query_parts = []
        parameters = []

        if driver_id:
            query_parts.append("c.assigned_driver = @driver_id")
            parameters.append({"name": "@driver_id", "value": driver_id})
        if driver_name:
            query_parts.append("CONTAINS(LOWER(c.driver_name), @driver_name)")
            parameters.append({"name": "@driver_name", "value": driver_name.lower()})
        if status:
            query_parts.append("c.current_status = @status")
            parameters.append({"name": "@status", "value": status})

        if not query_parts:
            return json.dumps({"found": False, "count": 0, "parcels": [], "error": "No search criteria provided"})

        query = f"SELECT * FROM c WHERE {' AND '.join(query_parts)} ORDER BY c.assigned_timestamp DESC"
        parcels = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        print(f"   ✅ Found {len(parcels)} parcels for driver")
        return json.dumps({"found": len(parcels) > 0, "count": len(parcels), "parcels": parcels,
                           "search_criteria": {"driver_id": driver_id, "driver_name": driver_name, "status": status}}, indent=2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"found": False, "error": str(e)})


def get_delivery_statistics_tool(state: str = None, date_from: str = None, date_to: str = None) -> str:
    """
    Tool for AI agents to get delivery statistics, optionally filtered by state.

    Args:
        state: Australian state (NSW, VIC, QLD, SA, WA, TAS, ACT, NT) - optional
        date_from: Start date (ISO format, optional)
        date_to: End date (ISO format, optional)

    Returns:
        JSON string with delivery statistics
    """
    print(f"🔧 Agent Tool: get_delivery_statistics_tool called with state={state}")

    try:
        container = _get_cosmos_container("parcels")

        if state:
            state = state.upper()
            query = "SELECT c.current_status, c.destination_state FROM c WHERE c.destination_state = @state"
            parameters = [{"name": "@state", "value": state}]
        else:
            query = "SELECT c.current_status, c.destination_state FROM c"
            parameters = []

        parcels = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        status_counts: Dict[str, int] = {}
        for p in parcels:
            s = p.get("current_status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        result: Dict[str, Any] = {"total_parcels": len(parcels), "status_breakdown": status_counts}
        if state:
            result["state_filter"] = state

        print(f"   ✅ Statistics - {len(parcels)} total parcels" + (f" in {state}" if state else ""))
        return json.dumps(result, indent=2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)})


def get_pending_parcels_for_dispatch_tool(state: str = None, max_count: int = 50) -> str:
    """
    Tool for Dispatcher agent to query parcels sitting at depot that need manifest assignment.

    Args:
        state: Optional Australian state filter (NSW, VIC, QLD, SA, WA, TAS, ACT, NT)
        max_count: Maximum number of parcels to return (default 50)

    Returns:
        JSON string with list of unassigned at-depot parcels grouped by postcode
    """
    print(f"🔧 Agent Tool: get_pending_parcels_for_dispatch_tool called - state={state}, max_count={max_count}")

    try:
        container = _get_cosmos_container("parcels")

        query_parts = [
            "LOWER(c.current_status) = 'at_depot'",
            "(NOT IS_DEFINED(c.assigned_driver) OR c.assigned_driver = null OR c.assigned_driver = '')",
        ]
        parameters = []

        if state:
            query_parts.append("c.destination_state = @state")
            parameters.append({"name": "@state", "value": state.upper()})

        query = (
            "SELECT c.barcode, c.tracking_number, c.recipient_name, c.recipient_address, "
            "c.destination_state, c.destination_postcode, c.destination_city, "
            "c.service_type, c.priority, c.registration_timestamp "
            f"FROM c WHERE {' AND '.join(query_parts)} "
            "ORDER BY c.registration_timestamp ASC"
        )

        parcels = list(
            container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True)
        )[:max_count]

        # Group by postcode for geographic dispatch planning
        by_postcode: Dict[str, List[str]] = {}
        for p in parcels:
            pc = p.get("destination_postcode") or "unknown"
            by_postcode.setdefault(pc, []).append(p.get("barcode") or p.get("tracking_number"))

        print(f"   ✅ Found {len(parcels)} pending parcels across {len(by_postcode)} postcodes")
        return json.dumps(
            {"total": len(parcels), "parcels": parcels, "grouped_by_postcode": by_postcode, "state_filter": state},
            indent=2,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e), "total": 0, "parcels": []})


def get_available_drivers_tool(state: str = None) -> str:
    """
    Tool for Dispatcher agent to list drivers available for assignment today.

    Args:
        state: Optional state filter — returns all drivers when omitted

    Returns:
        JSON string with list of drivers including their current active manifest count
    """
    print(f"🔧 Agent Tool: get_available_drivers_tool called - state={state}")

    try:
        users_container = _get_cosmos_container("users")
        manifests_container = _get_cosmos_container("driver_manifests")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        drivers = list(
            users_container.query_items(
                query="SELECT c.id, c.driver_id, c.username, c.name, c.full_name, c.state FROM c WHERE c.role = 'driver'",
                parameters=[],
                enable_cross_partition_query=True,
            )
        )

        if state:
            drivers = [d for d in drivers if not d.get("state") or d.get("state", "").upper() == state.upper()]

        result_drivers = []
        for driver in drivers:
            driver_id = driver.get("driver_id") or driver.get("username") or driver.get("id")
            try:
                counts = list(
                    manifests_container.query_items(
                        query=(
                            "SELECT VALUE COUNT(1) FROM c "
                            "WHERE c.driver_id = @did AND c.manifest_date = @today AND c.status = 'active'"
                        ),
                        parameters=[
                            {"name": "@did", "value": driver_id},
                            {"name": "@today", "value": today},
                        ],
                        enable_cross_partition_query=True,
                    )
                )
                active_manifests = counts[0] if counts else 0
            except Exception:
                active_manifests = 0

            result_drivers.append(
                {
                    "driver_id": driver_id,
                    "name": driver.get("name") or driver.get("full_name") or driver.get("username"),
                    "state": driver.get("state", ""),
                    "active_manifests_today": active_manifests,
                }
            )

        print(f"   ✅ Found {len(result_drivers)} available drivers")
        return json.dumps(
            {"total": len(result_drivers), "drivers": result_drivers, "state_filter": state}, indent=2
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e), "total": 0, "drivers": []})


def create_manifest_tool(driver_id: str, driver_name: str, tracking_numbers: List[str], reason: str = "") -> str:
    """
    Tool for Dispatcher agent to create a driver manifest.
    Resolves each tracking number/barcode, updates parcel status to in_transit,
    assigns the driver, and persists the manifest document.

    Args:
        driver_id: The driver's ID (e.g. 'driver-001')
        driver_name: The driver's display name
        tracking_numbers: List of tracking numbers or barcodes to include
        reason: Optional reason/notes for this manifest

    Returns:
        JSON string with manifest_id, items_count, and any unresolved barcodes
    """
    import uuid as _uuid

    print(
        f"🔧 Agent Tool: create_manifest_tool called - driver_id={driver_id}, "
        f"driver_name={driver_name}, parcels={len(tracking_numbers)}"
    )

    try:
        parcels_container = _get_cosmos_container("parcels")
        manifests_container = _get_cosmos_container("driver_manifests")

        manifest_id = f"manifest_{driver_id}_{_uuid.uuid4().hex[:8]}"
        manifest_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        manifest_items = []
        not_found = []

        for tn in tracking_numbers:
            parcels = list(
                parcels_container.query_items(
                    query="SELECT * FROM c WHERE c.tracking_number = @tn OR c.barcode = @tn",
                    parameters=[{"name": "@tn", "value": tn}],
                    enable_cross_partition_query=True,
                )
            )

            if not parcels:
                not_found.append(tn)
                continue

            parcel = parcels[0]
            parcel["assigned_driver"] = driver_id
            parcel["driver_name"] = driver_name
            parcel["current_status"] = "in_transit"
            parcel["manifest_id"] = manifest_id
            parcel["assigned_timestamp"] = now_iso
            parcels_container.upsert_item(body=parcel)

            manifest_items.append(
                {
                    "barcode": parcel.get("barcode"),
                    "tracking_number": parcel.get("tracking_number"),
                    "recipient_name": parcel.get("recipient_name"),
                    "recipient_address": parcel.get("recipient_address"),
                    "destination_state": parcel.get("destination_state"),
                    "destination_postcode": parcel.get("destination_postcode"),
                    "priority": parcel.get("priority", "normal"),
                    "status": "in_transit",
                }
            )

        if not manifest_items:
            return json.dumps({"success": False, "error": "No valid parcels found", "not_found": not_found})

        manifest_doc = {
            "id": manifest_id,
            "driver_id": driver_id,
            "driver_name": driver_name,
            "manifest_date": manifest_date,
            "status": "active",
            "items": manifest_items,
            "total_items": len(manifest_items),
            "reason": reason,
            "created_at": now_iso,
            "created_by": "dispatcher_agent",
        }
        manifests_container.upsert_item(body=manifest_doc)

        print(f"   ✅ Created manifest {manifest_id} with {len(manifest_items)} items for {driver_name}")
        return json.dumps(
            {
                "success": True,
                "manifest_id": manifest_id,
                "driver_id": driver_id,
                "driver_name": driver_name,
                "items_count": len(manifest_items),
                "not_found": not_found,
                "date": manifest_date,
            },
            indent=2,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"success": False, "error": str(e)})


def get_performance_metrics_tool(days_back: int = 7, state: str = None) -> str:
    """
    Tool for Optimization agent to retrieve rich delivery performance data.
    Surfaces card rate, delivery success, per-driver stats, and state breakdowns.

    Args:
        days_back: How many days of history to analyse (default 7)
        state: Optional Australian state filter

    Returns:
        JSON string with KPIs, anomalies, and driver performance table
    """
    print(f"🔧 Agent Tool: get_performance_metrics_tool called - days_back={days_back}, state={state}")

    try:
        container = _get_cosmos_container("parcels")
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

        if state:
            state = state.upper()
            query = (
                "SELECT c.current_status, c.destination_state, c.service_type, "
                "c.assigned_driver, c.driver_name, c.registration_timestamp, c.assigned_timestamp "
                "FROM c WHERE c.registration_timestamp >= @cutoff AND c.destination_state = @state"
            )
            parameters = [{"name": "@cutoff", "value": cutoff}, {"name": "@state", "value": state}]
        else:
            query = (
                "SELECT c.current_status, c.destination_state, c.service_type, "
                "c.assigned_driver, c.driver_name, c.registration_timestamp, c.assigned_timestamp "
                "FROM c WHERE c.registration_timestamp >= @cutoff"
            )
            parameters = [{"name": "@cutoff", "value": cutoff}]

        parcels = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

        total = len(parcels)
        if total == 0:
            return json.dumps({"warning": "No parcels found for this period", "days_back": days_back})

        status_counts: Dict[str, int] = {}
        for p in parcels:
            s = p.get("current_status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        delivered = status_counts.get("delivered", 0)
        carded = status_counts.get("carded", 0)
        delivery_attempted = delivered + carded
        card_rate = round(carded / delivery_attempted * 100, 1) if delivery_attempted > 0 else 0.0
        success_rate = round(delivered / delivery_attempted * 100, 1) if delivery_attempted > 0 else 0.0

        # Per-driver breakdown (top 10 by volume)
        driver_stats: Dict[str, Dict[str, int]] = {}
        for p in parcels:
            name = p.get("driver_name") or p.get("assigned_driver")
            if name:
                ds = driver_stats.setdefault(name, {"total": 0, "delivered": 0, "carded": 0})
                ds["total"] += 1
                if p.get("current_status") == "delivered":
                    ds["delivered"] += 1
                elif p.get("current_status") == "carded":
                    ds["carded"] += 1

        driver_table = {}
        for name, ds in sorted(driver_stats.items(), key=lambda x: x[1]["total"], reverse=True)[:10]:
            attempted = ds["delivered"] + ds["carded"]
            driver_table[name] = {
                "total": ds["total"],
                "delivered": ds["delivered"],
                "carded": ds["carded"],
                "success_rate_pct": round(ds["delivered"] / attempted * 100, 1) if attempted > 0 else None,
            }

        state_breakdown: Dict[str, int] = {}
        service_breakdown: Dict[str, int] = {}
        for p in parcels:
            st = p.get("destination_state", "unknown")
            state_breakdown[st] = state_breakdown.get(st, 0) + 1
            svc = p.get("service_type", "standard")
            service_breakdown[svc] = service_breakdown.get(svc, 0) + 1

        # Anomaly flags
        anomalies = []
        if card_rate > 20:
            anomalies.append(f"High card rate: {card_rate}% (threshold >20%)")
        if status_counts.get("at_depot", 0) > 50:
            anomalies.append(f"Large depot backlog: {status_counts['at_depot']} unassigned parcels")
        if success_rate < 75:
            anomalies.append(f"Low delivery success rate: {success_rate}% (threshold <75%)")

        result = {
            "period_days": days_back,
            "state_filter": state,
            "total_parcels": total,
            "status_breakdown": status_counts,
            "delivery_success_rate_pct": success_rate,
            "card_rate_pct": card_rate,
            "attempted_deliveries": delivery_attempted,
            "state_breakdown": state_breakdown,
            "service_breakdown": service_breakdown,
            "driver_performance": driver_table,
            "anomalies_detected": anomalies,
        }

        print(f"   ✅ Performance metrics: {total} parcels, {success_rate}% success, {card_rate}% card rate")
        return json.dumps(result, indent=2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool definitions for Azure AI Agent registration
# ---------------------------------------------------------------------------

# Customer Service Agent tools
CUSTOMER_SERVICE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "track_parcel",
            "description": "Call this function when the customer asks about a specific parcel by providing a tracking number or barcode. Use for queries like 'track [number]', 'where is [number]', 'status of [number]', 'parcel history for [barcode]', 'confirm recipient for [tracking number]'. Tracking numbers/barcodes can be any alphanumeric format: DT202512090001, DTVIC123456, OV69491491MM, OV77274939DA, etc. Do NOT call this for general questions (phone numbers, hours, services). Returns: barcode, status, sender name & address, recipient name & address, location, delivery estimate, and tracking history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The parcel tracking number or barcode - ANY alphanumeric code (DT*, DTVIC*, OV*, etc.)",
                    }
                },
                "required": ["tracking_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_parcels_by_recipient",
            "description": "Use this function to find parcels when the user provides a recipient name, address, and/or postcode, with optional date filtering. For example: 'find parcels for John Smith', 'parcels going to 1 Constitution Avenue', 'search parcels in postcode 3000', or 'how many parcels sent to [address] in the last 3 weeks'. Use days_back parameter for time-based queries (e.g., 7 for last week, 21 for last 3 weeks, 30 for last month). Returns a list of matching parcels with barcodes and creation dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_name": {
                        "type": "string",
                        "description": "The recipient's name to search for (e.g., 'John Smith')",
                    },
                    "address": {
                        "type": "string",
                        "description": "The delivery address to search for (e.g., '1 Constitution Avenue, Canberra ACT 2600')",
                    },
                    "postcode": {
                        "type": "string",
                        "description": "Australian postcode - 4 digits (e.g., '3000', '2000')",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back from today (e.g., 7 for last week, 21 for last 3 weeks, 30 for last month)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_parcels_by_driver",
            "description": "Call this function when the customer asks about parcels assigned to a specific driver. Use when the user mentions driver names (e.g., 'driver001', 'John Smith') or asks: 'show parcels for driver001', 'what parcels does John Smith have', 'parcels in transit for driver-002'. Can filter by status (in_transit, out_for_delivery, delivered). Returns list of parcels assigned to the driver with full details including barcode, recipient, address, status, and assigned timestamp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "driver_id": {
                        "type": "string",
                        "description": "The driver ID (e.g., 'driver-001', 'driver-002'). Extract from queries like 'driver001' → 'driver-001'",
                    },
                    "driver_name": {
                        "type": "string",
                        "description": "The driver's name to search for (e.g., 'John Smith', 'Maria Garcia')",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by parcel status: 'in_transit', 'out_for_delivery', 'delivered', or leave empty for all statuses",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_statistics",
            "description": "Use this function when the user asks about delivery statistics, status breakdowns, or how many parcels are in different states/regions. For example: 'how many parcels are in delivery?', 'show me delivery stats', 'delivery statistics for Victoria', 'how many parcels in WA?'. Can filter by Australian state (NSW, VIC, QLD, SA, WA, TAS, ACT, NT). Returns total parcel counts and status breakdown from Cosmos DB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Australian state code to filter by: NSW, VIC, QLD, SA, WA, TAS, ACT, or NT. Extract from queries like 'Victoria' → 'VIC', 'Western Australia' → 'WA', etc. Optional.",
                    },
                    "date_from": {"type": "string", "description": "Optional start date in ISO format (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "Optional end date in ISO format (YYYY-MM-DD)"},
                },
            },
        },
    },
]

# Dispatcher Agent tools
DISPATCHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_pending_parcels_for_dispatch",
            "description": "Query all parcels currently sitting at the depot that have not yet been assigned to a driver. Returns total count, full parcel details, and parcels grouped by postcode for geographic clustering. Call this first when asked to assign or dispatch parcels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Optional Australian state code (NSW, VIC, QLD, SA, WA, TAS, ACT, NT) to filter parcels.",
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of parcels to return. Default 50.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_drivers",
            "description": "Get the list of all active drivers, including how many manifests each has today. Use this to understand driver availability and workload before assigning parcels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Optional state filter to limit results to drivers in a specific Australian state.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_manifest",
            "description": "Create a driver manifest in the database. Call this once per driver after deciding which parcels to assign. Updates each parcel's status to in_transit and assigns the driver. Returns the manifest_id and count of items created.",
            "parameters": {
                "type": "object",
                "properties": {
                    "driver_id": {
                        "type": "string",
                        "description": "The driver's ID exactly as returned by get_available_drivers (e.g. 'driver-001').",
                    },
                    "driver_name": {"type": "string", "description": "The driver's display name."},
                    "tracking_numbers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tracking numbers or barcodes to include in this manifest.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason or note for this manifest (e.g. 'AI auto-assign — geographic cluster NSW').",
                    },
                },
                "required": ["driver_id", "driver_name", "tracking_numbers"],
            },
        },
    },
]

# Optimization Agent tools
OPTIMIZATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_delivery_statistics",
            "description": "Get overall delivery counts and status breakdown. Call proactively at the start of every session to surface the current network state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Optional Australian state code filter (NSW, VIC, QLD, SA, WA, TAS, ACT, NT).",
                    },
                    "date_from": {"type": "string", "description": "Optional start date in ISO format (YYYY-MM-DD)"},
                    "date_to": {"type": "string", "description": "Optional end date in ISO format (YYYY-MM-DD)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_metrics",
            "description": "Get rich delivery KPIs including card rate, delivery success rate, per-driver performance, state breakdowns, and auto-detected anomalies. Always call this proactively at the start of every session to look for issues before they are reported.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days of history to analyse. Default 7.",
                    },
                    "state": {
                        "type": "string",
                        "description": "Optional Australian state code filter (NSW, VIC, QLD, SA, WA, TAS, ACT, NT).",
                    },
                },
            },
        },
    },
]

# Full combined list (union of all per-agent sets) — used by TOOL_FUNCTIONS dispatch in base.py
AGENT_TOOLS = CUSTOMER_SERVICE_TOOLS + DISPATCHER_TOOLS + OPTIMIZATION_TOOLS


# Tool execution mapping — every tool callable dispatched through base.py
TOOL_FUNCTIONS = {
    # Customer Service Agent
    "track_parcel": track_parcel_tool,
    "search_parcels_by_recipient": search_parcels_by_recipient_tool,
    "search_parcels_by_driver": search_parcels_by_driver_tool,
    "get_delivery_statistics": get_delivery_statistics_tool,
    # Dispatcher Agent
    "get_pending_parcels_for_dispatch": get_pending_parcels_for_dispatch_tool,
    "get_available_drivers": get_available_drivers_tool,
    "create_manifest": create_manifest_tool,
    # Optimization Agent
    "get_performance_metrics": get_performance_metrics_tool,
}
