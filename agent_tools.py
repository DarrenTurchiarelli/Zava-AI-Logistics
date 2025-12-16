"""
Azure AI Agent Tools for Cosmos DB Integration
Provides tools for agents to query Cosmos DB directly for real-time data
"""

import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

# Import existing ParcelTrackingDB for consistent access
from parcel_tracking_db import ParcelTrackingDB

load_dotenv()


async def track_parcel_tool(tracking_number: str) -> str:
    """
    Tool for AI agents to track a parcel in real-time from Cosmos DB.
    Uses existing ParcelTrackingDB for consistent access.
    
    Args:
        tracking_number: The parcel tracking number to look up
        
    Returns:
        JSON string with parcel status, location, and tracking history
    """
    print(f"🔧 Agent Tool: track_parcel_tool called with tracking_number={tracking_number}")
    
    try:
        # Ensure environment variables are loaded in this thread context
        load_dotenv(override=True)
        
        # Use existing ParcelTrackingDB for consistent access
        async with ParcelTrackingDB() as db:
            # Search by tracking_number, barcode, or id (method now searches all)
            parcel = await db.get_parcel_by_tracking_number(tracking_number)
            
            if not parcel:
                print(f"   ❌ Parcel not found with identifier: {tracking_number}")
                return json.dumps({
                    "found": False,
                    "message": f"No parcel found with identifier {tracking_number}",
                    "tracking_number": tracking_number
                })
            
            # Get tracking events (method searches by barcode, tracking_number, or id)
            events = await db.get_parcel_tracking_history(tracking_number)
            
            # Build response
            result = {
                "found": True,
                "tracking_number": parcel.get("tracking_number"),
                "status": parcel.get("status"),
                "current_location": parcel.get("current_location"),
                "destination": parcel.get("destination"),
                "estimated_delivery": parcel.get("estimated_delivery"),
                "service_type": parcel.get("service_type"),
                "created_at": parcel.get("created_at"),
                "sender_name": parcel.get("sender", {}).get("name") if parcel.get("sender") else None,
                "recipient_name": parcel.get("recipient", {}).get("name"),
                "recipient_postcode": parcel.get("recipient", {}).get("postcode"),
                "recent_events": [
                    {
                        "timestamp": e.get("timestamp"),
                        "status": e.get("status"),
                        "location": e.get("location"),
                        "description": e.get("description")
                    }
                    for e in (events[:5] if events else [])
                ],
                "total_events": len(events) if events else 0
            }
            
            print(f"   ✅ Found parcel - Sender: {result['sender_name']}, Recipient: {result['recipient_name']}, Status: {result['status']}")
            return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "found": False,
            "error": str(e),
            "tracking_number": tracking_number
        }
        print(f"   ❌ Agent Tool Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return json.dumps(error_result)


async def search_parcels_by_recipient_tool(recipient_name: str = None, postcode: str = None) -> str:
    """
    Tool for AI agents to search parcels by recipient name or postcode.
    
    Args:
        recipient_name: Recipient name to search for (optional)
        postcode: Postcode to search for (optional)
        
    Returns:
        JSON string with list of matching parcels
    """
    print(f"🔧 Agent Tool: search_parcels_by_recipient_tool called")
    
    try:
        # Initialize Cosmos DB client
        if USE_COSMOS_KEY and COSMOS_KEY:
            client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        else:
            # Use Managed Identity when explicitly enabled (Azure deployment)
            if os.getenv('USE_MANAGED_IDENTITY', 'false').lower() == 'true':
                credential = ManagedIdentityCredential()
            else:
                credential = DefaultAzureCredential(exclude_developer_cli_credential=True)
            client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
        
        database = client.get_database_client(COSMOS_DATABASE)
        parcels_container = database.get_container_client("parcels")
        
        # Build query based on provided parameters
        if recipient_name and postcode:
            query = """
                SELECT c.tracking_number, c.status, c.current_location, c.estimated_delivery, 
                       c.recipient.name as recipient_name, c.recipient.postcode as postcode
                FROM c 
                WHERE CONTAINS(LOWER(c.recipient.name), @name) 
                AND c.recipient.postcode = @postcode
            """
            parameters = [
                {"name": "@name", "value": recipient_name.lower()},
                {"name": "@postcode", "value": postcode}
            ]
        elif recipient_name:
            query = """
                SELECT c.tracking_number, c.status, c.current_location, c.estimated_delivery,
                       c.recipient.name as recipient_name, c.recipient.postcode as postcode
                FROM c 
                WHERE CONTAINS(LOWER(c.recipient.name), @name)
            """
            parameters = [{"name": "@name", "value": recipient_name.lower()}]
        elif postcode:
            query = """
                SELECT c.tracking_number, c.status, c.current_location, c.estimated_delivery,
                       c.recipient.name as recipient_name, c.recipient.postcode as postcode
                FROM c 
                WHERE c.recipient.postcode = @postcode
            """
            parameters = [{"name": "@postcode", "value": postcode}]
        else:
            return json.dumps({
                "found": False,
                "message": "Please provide at least recipient name or postcode to search"
            })
        
        parcels = []
        async for item in parcels_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            parcels.append(item)
        
        await client.close()
        
        result = {
            "found": len(parcels) > 0,
            "count": len(parcels),
            "parcels": parcels[:10]  # Limit to 10 results
        }
        
        print(f"✅ Agent Tool: Found {len(parcels)} parcels")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "found": False,
            "error": str(e)
        }
        print(f"❌ Agent Tool Error: {str(e)}")
        return json.dumps(error_result)


async def get_delivery_statistics_tool(date_from: str = None, date_to: str = None) -> str:
    """
    Tool for AI agents to get delivery statistics.
    
    Args:
        date_from: Start date (ISO format, optional)
        date_to: End date (ISO format, optional)
        
    Returns:
        JSON string with delivery statistics
    """
    print(f"🔧 Agent Tool: get_delivery_statistics_tool called")
    
    try:
        # Initialize Cosmos DB client
        if USE_COSMOS_KEY and COSMOS_KEY:
            client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        else:
            # Use Managed Identity when explicitly enabled (Azure deployment)
            if os.getenv('USE_MANAGED_IDENTITY', 'false').lower() == 'true':
                credential = ManagedIdentityCredential()
            else:
                credential = DefaultAzureCredential(exclude_developer_cli_credential=True)
            client = CosmosClient(COSMOS_ENDPOINT, credential=credential)
        
        database = client.get_database_client(COSMOS_DATABASE)
        parcels_container = database.get_container_client("parcels")
        
        # Query for statistics
        query = "SELECT c.status FROM c"
        parameters = []
        
        parcels = []
        async for item in parcels_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            parcels.append(item)
        
        await client.close()
        
        # Calculate statistics
        status_counts = {}
        for parcel in parcels:
            status = parcel.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        result = {
            "total_parcels": len(parcels),
            "status_breakdown": status_counts
        }
        
        print(f"✅ Agent Tool: Statistics - {len(parcels)} total parcels")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        error_result = {
            "error": str(e)
        }
        print(f"❌ Agent Tool Error: {str(e)}")
        return json.dumps(error_result)


# Tool definitions for Azure AI Agent registration
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "track_parcel",
            "description": "**CRITICAL: ALWAYS call this function when user mentions ANY tracking number or asks about parcel details.** This includes questions like 'who is the sender of [number]', 'where is [number]', 'track [number]', 'status of [number]'. Tracking numbers can be ANY alphanumeric format: DT202512090001, DTVIC123456, OV69491491MM, OV77274939DA, etc. The database contains ALL tracking formats. DO NOT assume a tracking number is invalid - ALWAYS call this function to check. Returns: status, sender name, recipient, location, delivery estimate, and tracking history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The parcel tracking number - ANY alphanumeric code (DT*, DTVIC*, OV*, etc.)"
                    }
                },
                "required": ["tracking_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_parcels_by_recipient",
            "description": "Use this function to find parcels when the user provides a recipient name and/or postcode but doesn't have a tracking number. For example: 'find parcels for John Smith' or 'search parcels in postcode 3000'. Returns a list of matching parcels from Cosmos DB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_name": {
                        "type": "string",
                        "description": "The recipient's name to search for (e.g., 'John Smith')"
                    },
                    "postcode": {
                        "type": "string",
                        "description": "Australian postcode - 4 digits (e.g., '3000', '2000')"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_statistics",
            "description": "Use this function when the user asks about delivery statistics, status breakdowns, or how many parcels are in different states. For example: 'how many parcels are in delivery?' or 'show me delivery stats'. Returns total parcel counts and status breakdown from Cosmos DB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Optional start date in ISO format (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Optional end date in ISO format (YYYY-MM-DD)"
                    }
                }
            }
        }
    }
]


# Tool execution mapping
TOOL_FUNCTIONS = {
    "track_parcel": track_parcel_tool,
    "search_parcels_by_recipient": search_parcels_by_recipient_tool,
    "get_delivery_statistics": get_delivery_statistics_tool
}
