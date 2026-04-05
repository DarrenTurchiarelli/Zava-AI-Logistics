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


# Tool definitions for Azure AI Agent registration
AGENT_TOOLS = [
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


# Tool execution mapping
TOOL_FUNCTIONS = {
    "track_parcel": track_parcel_tool,
    "search_parcels_by_recipient": search_parcels_by_recipient_tool,
    "search_parcels_by_driver": search_parcels_by_driver_tool,
    "get_delivery_statistics": get_delivery_statistics_tool,
}
