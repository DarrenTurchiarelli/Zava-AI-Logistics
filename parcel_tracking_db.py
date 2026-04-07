#!/usr/bin/env python3
"""
Consolidated Parcel Tracking Database Interface

This module provides a comprehensive interface for Azure Cosmos DB operations
for last mile logistics parcel tracking, including:
- Parcel registration and management
- Tracking events and delivery attempts
- Approval workflows
- Store-specific operations
- Setup and testing utilities

Usage:
    from parcel_tracking_db import ParcelTrackingDB

    # Initialize database
    db = ParcelTrackingDB()

    # Register a parcel
    parcel = await db.register_parcel(
        barcode="ABC123456",
        sender_name="John Smith",
        recipient_name="Jane Doe",
        recipient_address="123 Main St, Sydney, NSW 2000"
    )

    # Request approval
    request_id = await db.request_approval(
        "ABC123456",
        "delivery_redirect",
        "Customer requested address change"
    )
"""

import asyncio
import os
import random
import string
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv

# Suppress aiohttp warnings for cleaner output
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed")

from azure.cosmos import PartitionKey, exceptions

# Azure imports
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential

# Test data generation
from faker import Faker

# Load environment variables
load_dotenv()

# Initialize Faker for generating test data with Australian locale
fake = Faker("en_AU")

# Global credential cache for AzureCliCredential only (spawns subprocess - slow to create)
# ManagedIdentityCredential is NOT cached because async credentials are tied to their
# creation event loop. When tools run in new threads with new event loops, a stale
# credential fails silently causing false "not found" responses from Cosmos DB queries.
_cached_cli_credential = None


def get_cached_credential():
    """Get an Azure credential appropriate for the current execution context.
    
    ManagedIdentityCredential: always creates fresh (async, event-loop-bound).
    AzureCliCredential: cached singleton (subprocess-based, loop-independent).
    """
    global _cached_cli_credential
    if os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true":
        # Always create fresh - ManagedIdentityCredential holds an aiohttp session
        # that is bound to the event loop in which it is first used. Reusing it
        # across threads/event loops causes silent query failures.
        return ManagedIdentityCredential()
    else:
        # AzureCliCredential spawns `az` subprocess on every get_token(); caching
        # the Python object is safe since it has no internal aiohttp session.
        if _cached_cli_credential is None:
            _cached_cli_credential = AzureCliCredential(process_timeout=60)
        return _cached_cli_credential


class ParcelTrackingDB:
    """
    Consolidated Parcel Tracking Database Interface

    Authentication Methods:
    1. Key-based (Local Development):
       - Set COSMOS_CONNECTION_STRING or COSMOS_DB_ENDPOINT + COSMOS_DB_KEY

    2. Managed Identity (Azure Production):
       - Set USE_MANAGED_IDENTITY=true
       - Set COSMOS_DB_ENDPOINT and COSMOS_DB_DATABASE_NAME
       - Required RBAC: Cosmos DB Built-in Data Contributor (00000000-0000-0000-0000-000000000002)
       - See Scripts/setup_rbac_permissions.ps1 for setup
       - See Guides/DEPLOYMENT.md#rbac-permissions for details
    """

    def __init__(self):
        # Try to get individual values first
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")

        # If not available, parse from connection string
        if not self.endpoint or not self.key:
            connection_string = os.getenv("COSMOS_CONNECTION_STRING")
            if connection_string:
                # Parse connection string
                parts = dict(part.split("=", 1) for part in connection_string.split(";") if "=" in part)
                self.endpoint = parts.get("AccountEndpoint", "").rstrip("/")
                self.key = parts.get("AccountKey", "")
                print(
                    f"🔍 DEBUG: Parsed connection string - endpoint: {self.endpoint[:50] if self.endpoint else 'None'}, key length: {len(self.key) if self.key else 0}"
                )

        self.database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "agent_workflow_db")

        # Container names
        self.parcels_container = "parcels"
        self.tracking_events_container = "tracking_events"
        self.delivery_attempts_container = "delivery_attempts"
        self.feedback_container = "feedback"
        self.company_info_container = "company_info"
        self.suspicious_messages_container = "suspicious_messages"
        self.address_history_container = "address_history"

        # Connection objects
        self.client = None
        self.database = None
        self.credential = None
        self.using_azure_ad = False  # Track if we're using Azure AD (to skip operations requiring elevated permissions)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Initialize connection to Cosmos DB"""
        try:
            if not self.endpoint:
                raise ValueError("COSMOS_DB_ENDPOINT or COSMOS_CONNECTION_STRING environment variable is required")

            # Try key-based authentication first
            if self.key:
                # Check if we should force key-based auth (for data generation scripts)
                force_key_auth = os.getenv("FORCE_KEY_AUTH", "false").lower() == "true"
                
                try:
                    # Use key-based authentication
                    self.client = CosmosClient(self.endpoint, self.key)

                    # Test the connection by attempting to access the database
                    self.database = await self.client.create_database_if_not_exists(
                        id=self.database_name, offer_throughput=400
                    )
                    # Only print in debug mode
                    if os.getenv("DEBUG_MODE") == "true":
                        print(f"✓ Connected to Cosmos DB using account key")

                except Exception as key_error:
                    # If forcing key auth, don't fall back to Azure AD
                    if force_key_auth:
                        print(f"[ERROR] Key-based authentication failed (FORCE_KEY_AUTH=true, not falling back to Azure AD)")
                        print(f"[ERROR] {str(key_error)[:200]}")
                        raise key_error
                    
                    # If key auth fails, only try Azure AD if the error suggests it
                    if "Local Authorization is disabled" in str(key_error):
                        if os.getenv("DEBUG_MODE") == "true":
                            print(f"[WARN] Key-based auth disabled, trying Azure AD...")
                        # Use cached credential to avoid re-authentication timeout
                        self.credential = get_cached_credential()
                        self.client = CosmosClient(self.endpoint, self.credential)
                        self.using_azure_ad = True  # Mark that we're using Azure AD

                        # Just get the database client (don't try to create - requires readMetadata permission)
                        self.database = self.client.get_database_client(self.database_name)
                        if os.getenv("DEBUG_MODE") == "true":
                            print(f"✓ Connected to Cosmos DB using Azure AD (AzureCliCredential)")
                    else:
                        # For other errors, re-raise them
                        print(f"[ERROR] Cosmos DB connection failed: {key_error}")
                        raise key_error
            else:
                # No key provided - must use Azure AD
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"[WARN] No account key found, trying Azure AD authentication...")
                # Use cached credential to avoid re-authentication timeout
                self.credential = get_cached_credential()
                self.client = CosmosClient(self.endpoint, self.credential)
                self.using_azure_ad = True  # Mark that we're using Azure AD

                # Just get the database client (don't try to create - requires readMetadata permission)
                self.database = self.client.get_database_client(self.database_name)
                if os.getenv("DEBUG_MODE") == "true":
                    print(f"✓ Connected to Cosmos DB using Azure AD (AzureCliCredential)")

            # Create containers if they don't exist (skip if using Azure AD without elevated permissions)
            if not self.using_azure_ad:
                try:
                    await self._create_containers()
                except Exception as container_error:
                    # If container creation fails, assume they already exist (common with Azure AD limited permissions)
                    print(f"[WARN] Skipping container creation: {str(container_error)[:100]}")

            # Database connection successful - ready for operations

        except Exception as e:
            print(f"[ERROR] Failed to connect to Cosmos DB: {e}")
            raise

    async def _create_containers(self):
        """Create ALL containers with appropriate partition keys"""
        containers = [
            {
                "id": self.parcels_container,
                "partition_key": PartitionKey(path="/store_location"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.tracking_events_container,
                "partition_key": PartitionKey(path="/barcode"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.delivery_attempts_container,
                "partition_key": PartitionKey(path="/barcode"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.feedback_container,
                "partition_key": PartitionKey(path="/tracking_number"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.company_info_container,
                "partition_key": PartitionKey(path="/info_type"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.suspicious_messages_container,
                "partition_key": PartitionKey(path="/report_date"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": self.address_history_container,
                "partition_key": PartitionKey(path="/address_normalized"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            # Additional containers previously created by separate scripts
            {
                "id": "users",
                "partition_key": PartitionKey(path="/username"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
            {
                "id": "driver_manifests",
                "partition_key": PartitionKey(path="/driver_id"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
                "default_ttl": 2592000,  # 30 days — manifests accumulate daily; auto-expire old ones
            },
            {
                "id": "address_notes",
                "partition_key": PartitionKey(path="/address_normalized"),
                "indexing_policy": {"indexingMode": "consistent", "automatic": True, "includedPaths": [{"path": "/*"}]},
            },
        ]

        for container_spec in containers:
            try:
                ttl_kwargs = {}
                if "default_ttl" in container_spec:
                    ttl_kwargs["default_ttl"] = container_spec["default_ttl"]
                await self.database.create_container_if_not_exists(
                    id=container_spec["id"],
                    partition_key=container_spec["partition_key"],
                    indexing_policy=container_spec["indexing_policy"],
                    **ttl_kwargs,
                )
                print(f"✓ Container ready: {container_spec['id']}")
            except Exception as e:
                # Log error but don't fail - some containers might be optional
                print(f"⚠️ Container creation warning for {container_spec['id']}: {str(e)[:100]}")

    async def close(self):
        """Close database connections and cleanup resources"""
        try:
            if self.client:
                # Properly close the aiohttp client session
                if hasattr(self.client, "_client_connection"):
                    try:
                        connection = self.client._client_connection
                        if connection and not connection.closed:
                            await connection.close()
                    except Exception:
                        pass

                # Close the Cosmos client
                if hasattr(self.client, "close"):
                    try:
                        result = self.client.close()
                        # If it returns a coroutine, await it
                        if hasattr(result, "__await__"):
                            await result
                    except Exception:
                        pass
                self.client = None

            if self.credential:
                # Close Azure credentials properly
                if hasattr(self.credential, "close") and callable(getattr(self.credential, "close")):
                    try:
                        if asyncio.iscoroutinefunction(self.credential.close):
                            await self.credential.close()
                        else:
                            self.credential.close()
                    except Exception:
                        pass
                self.credential = None
        except Exception:
            # Silently ignore all close errors to prevent blocking
            pass

    # ==================== PARCEL MANAGEMENT ====================

    async def register_parcel(
        self,
        barcode: str,
        sender_name: str,
        sender_address: str,
        sender_phone: Optional[str],
        recipient_name: str,
        recipient_address: str,
        recipient_phone: Optional[str],
        destination_postcode: str,
        destination_state: str,
        destination_city: Optional[str] = None,
        service_type: str = "standard",
        weight: Optional[float] = None,
        dimensions: Optional[str] = None,
        declared_value: Optional[float] = None,
        special_instructions: Optional[str] = None,
        store_location: str = "unknown",
        current_status: Optional[str] = None,  # Allow setting initial status
        origin_location: Optional[str] = None,  # Allow setting DC
        current_location: Optional[str] = None,  # Allow setting initial location
        fraud_risk_score: Optional[int] = None,  # Allow setting risk score
    ) -> Dict[str, Any]:
        """Register a new parcel into the logistics network"""
        container = self.database.get_container_client(self.parcels_container)

        # Check if barcode already exists to prevent duplicates
        existing_parcel = await self.get_parcel_by_barcode(barcode)
        if existing_parcel:
            print(
                f"⚠️  Parcel with barcode {barcode} already exists (Tracking: {existing_parcel.get('tracking_number')})"
            )
            raise ValueError(f"Duplicate barcode: Parcel {barcode} already exists in the system")

        # Generate tracking number
        tracking_number = self._generate_tracking_number()

        # Use provided values or defaults
        status = current_status or "registered"
        location = current_location or store_location

        parcel = {
            "id": str(uuid.uuid4()),
            "barcode": barcode,
            "tracking_number": tracking_number,
            "sender_name": sender_name,
            "sender_address": sender_address,
            "sender_phone": sender_phone,
            "recipient_name": recipient_name,
            "recipient_address": recipient_address,
            "recipient_phone": recipient_phone,
            "destination_postcode": destination_postcode,
            "destination_state": destination_state,
            "destination_city": destination_city,
            "service_type": service_type,
            "weight": weight,
            "dimensions": dimensions,
            "declared_value": declared_value,
            "special_instructions": special_instructions,
            "store_location": store_location,
            "registration_timestamp": datetime.now(timezone.utc).isoformat(),
            "current_status": status,
            "current_location": location,
            "estimated_delivery": self._calculate_estimated_delivery(service_type),
            "delivery_attempts": 0,
            "is_delivered": False,
        }

        # Add optional fields if provided
        if origin_location:
            parcel["origin_location"] = origin_location
        if fraud_risk_score is not None:
            parcel["fraud_risk_score"] = fraud_risk_score

        try:
            created_parcel = await container.create_item(body=parcel)
            print(f"✅ Parcel registered: {barcode} → {tracking_number}")

            # Create initial tracking event
            await self.create_tracking_event(
                barcode=barcode,
                event_type="registered",
                location=store_location,
                description=f"Parcel registered for {recipient_name}",
            )

            # Add to address history (optional - don't fail if container doesn't exist)
            try:
                await self.add_address_delivery(
                    address=recipient_address,
                    parcel_barcode=barcode,
                    recipient_name=recipient_name,
                    sender_name=sender_name,
                    notes=special_instructions,
                )
            except Exception as addr_error:
                # Address history is optional - log but don't fail registration
                print(f"⚠️ Could not update address history: {addr_error}")

            return created_parcel
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error registering parcel: {e}")
            raise

    async def get_all_parcels(self) -> List[Dict[str, Any]]:
        """Get all parcels in the system"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            items = container.query_items(query="SELECT * FROM c")
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcels: {e}")
            return []

    async def get_parcel_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Get a specific parcel by barcode"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.barcode = @barcode", parameters=[{"name": "@barcode", "value": barcode}]
            )
            parcels = [item async for item in items]
            return parcels[0] if parcels else None
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcel by barcode: {e}")
            return None

    async def get_parcel_by_tracking_number(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Get a specific parcel by tracking number, barcode, or id"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            # Search by tracking_number, barcode, or id
            items = container.query_items(
                query="""SELECT * FROM c
                         WHERE c.tracking_number = @id1
                         OR c.barcode = @id2
                         OR c.id = @id3""",
                parameters=[
                    {"name": "@id1", "value": tracking_number},
                    {"name": "@id2", "value": tracking_number},
                    {"name": "@id3", "value": tracking_number},
                ],
            )
            parcels = [item async for item in items]
            return parcels[0] if parcels else None
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcel by tracking number: {e}")
            raise  # Re-raise so callers can distinguish error from not-found

    async def search_parcels_by_recipient(
        self, recipient_name: str = None, postcode: str = None, address: str = None, days_back: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search parcels by recipient information with optional date filtering

        Args:
            recipient_name: Recipient name to search for (optional)
            postcode: Postcode to search for (optional)
            address: Full or partial address to search for (optional)
            days_back: Number of days to look back from today (optional)

        Returns:
            List of matching parcels
        """
        container = self.database.get_container_client(self.parcels_container)

        try:
            # Build query based on provided parameters
            query_parts = []
            parameters = []

            if recipient_name:
                query_parts.append("CONTAINS(LOWER(c.recipient_name), @name)")
                parameters.append({"name": "@name", "value": recipient_name.lower()})

            if postcode:
                query_parts.append("c.destination_postcode = @postcode")
                parameters.append({"name": "@postcode", "value": postcode})

            if address:
                query_parts.append("CONTAINS(LOWER(c.recipient_address), @address)")
                parameters.append({"name": "@address", "value": address.lower()})

            # Add date filtering if days_back is provided
            if days_back:
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
                query_parts.append("c.created_at >= @cutoff_date")
                parameters.append({"name": "@cutoff_date", "value": cutoff_date})

            if not query_parts:
                return []

            where_clause = " AND ".join(query_parts)
            # Return full documents instead of projected fields for compatibility
            query = f"""
                SELECT * FROM c
                WHERE {where_clause}
                ORDER BY c.created_at DESC
            """

            parcels = []
            async for item in container.query_items(query=query, parameters=parameters):
                parcels.append(item)

            return parcels[:20]  # Limit to 20 results

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error searching parcels by recipient: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def search_parcels_by_driver(
        self, driver_id: str = None, driver_name: str = None, status: str = None
    ) -> List[Dict[str, Any]]:
        """
        Search parcels assigned to a specific driver

        Args:
            driver_id: Driver ID to search for (e.g., 'driver-001')
            driver_name: Driver name to search for (optional)
            status: Filter by parcel status (e.g., 'in_transit', 'out_for_delivery')

        Returns:
            List of matching parcels
        """
        container = self.database.get_container_client(self.parcels_container)

        try:
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
                return []

            where_clause = " AND ".join(query_parts)
            query = f"""
                SELECT * FROM c
                WHERE {where_clause}
                ORDER BY c.assigned_timestamp DESC
            """

            parcels = []
            async for item in container.query_items(query=query, parameters=parameters):
                parcels.append(item)

            return parcels

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error searching parcels by driver: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def update_parcel_status(self, barcode: str, status: str, location: str, scanned_by: str = "system") -> bool:
        """Update the status and location of a parcel"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            # Find the parcel first
            parcel = await self.get_parcel_by_barcode(barcode)
            if not parcel:
                print(f"❌ Parcel not found: {barcode}")
                return False

            # Update the parcel
            parcel["current_status"] = status
            parcel["current_location"] = location
            parcel["last_updated"] = datetime.now(timezone.utc).isoformat()

            if status == "Delivered":
                parcel["is_delivered"] = True
                parcel["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()

            await container.replace_item(item=parcel, body=parcel)

            # Create tracking event
            await self.create_tracking_event(
                barcode=barcode,
                event_type=status,
                location=location,
                description=f"Parcel status updated to {status}",
                scanned_by=scanned_by,
            )

            print(f"✅ Parcel status updated: {barcode} → {status}")
            return True

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error updating parcel status: {e}")
            return False

    async def store_delivery_photo(self, barcode: str, photo_base64: str, uploaded_by: str = "driver") -> bool:
        """Store delivery photo proof in parcel record"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            # Find the parcel first
            parcel = await self.get_parcel_by_barcode(barcode)
            if not parcel:
                print(f"❌ Parcel not found: {barcode}")
                return False

            # Add delivery photo to parcel
            if "delivery_photos" not in parcel:
                parcel["delivery_photos"] = []

            parcel["delivery_photos"].append(
                {
                    "photo_data": photo_base64,
                    "uploaded_by": uploaded_by,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "photo_size_kb": round(len(photo_base64) * 3 / 4 / 1024, 1),  # approx decoded size
                }
            )

            parcel["last_updated"] = datetime.now(timezone.utc).isoformat()

            await container.replace_item(item=parcel, body=parcel)

            print(f"✅ Delivery photo stored for: {barcode}")
            return True

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error storing delivery photo: {e}")
            return False

    async def store_lodgement_photo(self, barcode: str, photo_base64: str, uploaded_by: str = "customer") -> bool:
        """Store lodgement photo (initial registration) in parcel record"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            # Find the parcel first
            parcel = await self.get_parcel_by_barcode(barcode)
            if not parcel:
                print(f"❌ Parcel not found: {barcode}")
                return False

            # Add lodgement photo to parcel
            if "lodgement_photos" not in parcel:
                parcel["lodgement_photos"] = []

            parcel["lodgement_photos"].append(
                {
                    "photo_data": photo_base64,
                    "uploaded_by": uploaded_by,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "photo_size_kb": round(len(photo_base64) * 3 / 4 / 1024, 1),  # approx decoded size
                }
            )

            parcel["last_updated"] = datetime.now(timezone.utc).isoformat()

            await container.replace_item(item=parcel, body=parcel)

            print(f"✅ Lodgement photo stored for: {barcode}")
            return True

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error storing lodgement photo: {e}")
            return False

    async def scan_parcel_at_location(
        self, barcode: str, scan_location: str, scanned_by: str = "system", scan_type: str = "arrival"
    ) -> Dict[str, Any]:
        """
        Smart location-aware parcel scanning with Azure AI Driver Agent integration
        Updates status and location based on scan location

        Args:
            barcode: Parcel barcode
            scan_location: Where the parcel was scanned (e.g., "Depot_Melbourne", "Store_Sydney_CBD", "Vehicle_001")
            scanned_by: Who scanned it
            scan_type: Type of scan - "arrival", "departure", "processing", "loading", "delivered"

        Returns:
            Dictionary with scan result and updated parcel info
        """
        try:
            # Call Azure AI Driver Agent for delivery execution intelligence
            from src.infrastructure.agents import driver_agent

            container = self.database.get_container_client(self.parcels_container)

            # Find the parcel
            parcel = await self.get_parcel_by_barcode(barcode)
            if not parcel:
                return {"success": False, "error": f"Parcel not found: {barcode}", "scan_location": scan_location}

            # Determine new status and location based on scan location and current status
            current_status = parcel.get("current_status", "registered")
            current_location = parcel.get("current_location", "unknown")

            # Prepare data for Azure AI Driver Agent
            delivery_action = {
                "action_type": "scan",
                "tracking_number": parcel.get("tracking_number", barcode),
                "location": scan_location,
                "scan_type": scan_type,
                "driver_id": scanned_by,
                "current_status": current_status,
                "recipient_address": parcel.get("recipient_address", "Unknown"),
            }

            # Call Azure AI Driver Agent (async, don't block on failure)
            try:
                agent_result = await driver_agent(delivery_action)
                if agent_result.get("success"):
                    print(f"   [AI] Driver Agent processed scan")
            except Exception as ai_error:
                print(f"   [WARN] AI Driver Agent unavailable: {ai_error}")

            # Smart status determination based on scan location
            new_status, description = self._determine_status_from_location(scan_location, current_status, scan_type)

            # Update parcel location and status
            parcel["current_status"] = new_status
            parcel["current_location"] = scan_location
            parcel["last_updated"] = datetime.now(timezone.utc).isoformat()
            parcel["last_scanned_by"] = scanned_by
            parcel["last_scan_type"] = scan_type

            # Handle delivery completion
            if new_status == "Delivered":
                parcel["is_delivered"] = True
                parcel["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()
                parcel["delivery_attempts"] = parcel.get("delivery_attempts", 0) + 1

            # Update parcel in database
            await container.replace_item(item=parcel, body=parcel)

            # Create detailed tracking event
            await self.create_tracking_event(
                barcode=barcode,
                event_type=new_status,
                location=scan_location,
                description=description,
                scanned_by=scanned_by,
                additional_info={
                    "scan_type": scan_type,
                    "previous_location": current_location,
                    "previous_status": current_status,
                    "transition": f"{current_location} → {scan_location}",
                },
            )

            return {
                "success": True,
                "barcode": barcode,
                "previous_location": current_location,
                "current_location": scan_location,
                "previous_status": current_status,
                "current_status": new_status,
                "description": description,
                "scanned_by": scanned_by,
                "scan_type": scan_type,
                "timestamp": parcel["last_updated"],
            }

        except exceptions.CosmosHttpResponseError as e:
            return {
                "success": False,
                "error": f"Database error: {e}",
                "barcode": barcode,
                "scan_location": scan_location,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "barcode": barcode,
                "scan_location": scan_location,
            }

    def _determine_status_from_location(
        self, scan_location: str, current_status: str, scan_type: str
    ) -> tuple[str, str]:
        """
        Determine the appropriate status based on scan location, current status, and scan type

        Returns:
            Tuple of (new_status, description)
        """
        scan_location_lower = scan_location.lower()

        # Store scanning (initial registration or return)
        if "store" in scan_location_lower:
            if current_status == "Registered":
                return "In Transit", f"Parcel collected from store and in transit to depot"
            else:
                return "At Store", f"Parcel scanned at {scan_location}"

        # Depot/Facility scanning
        elif any(keyword in scan_location_lower for keyword in ["depot", "facility", "warehouse", "sorting"]):
            if scan_type == "arrival":
                return "At Depot", f"Parcel arrived at {scan_location} for sorting and processing"
            elif scan_type == "departure":
                return "In Transit", f"Parcel departed {scan_location} for delivery route"
            elif scan_type == "processing":
                return "At Depot", f"Parcel being processed at {scan_location}"
            else:
                return "At Depot", f"Parcel scanned at {scan_location}"

        # Vehicle scanning (delivery truck, van, etc.)
        elif any(keyword in scan_location_lower for keyword in ["vehicle", "truck", "van", "delivery"]):
            if scan_type == "loading":
                return "Out for Delivery", f"Parcel loaded onto {scan_location} for delivery"
            elif scan_type == "arrival":
                return "Out for Delivery", f"Parcel on {scan_location} approaching destination"
            else:
                return "Out for Delivery", f"Parcel on {scan_location}"

        # Customer location scanning (delivery completion)
        elif any(keyword in scan_location_lower for keyword in ["customer", "recipient", "address", "delivery"]):
            return "Delivered", f"Parcel delivered to customer at {scan_location}"

        # Hub scanning (major sorting/distribution centers)
        elif any(keyword in scan_location_lower for keyword in ["hub", "distribution", "center"]):
            if scan_type == "arrival":
                return "At Depot", f"Parcel arrived at distribution hub {scan_location}"
            elif scan_type == "departure":
                return "In Transit", f"Parcel departed distribution hub {scan_location}"
            else:
                return "At Depot", f"Parcel at distribution hub {scan_location}"

        # Default case - generic location
        else:
            if scan_type == "arrival":
                return "In Transit", f"Parcel arrived at {scan_location}"
            elif scan_type == "departure":
                return "In Transit", f"Parcel departed {scan_location}"
            else:
                return "In Transit", f"Parcel scanned at {scan_location}"

    # ==================== TRACKING EVENTS ====================

    async def create_tracking_event(
        self,
        barcode: str,
        event_type: str,
        location: str,
        description: str,
        scanned_by: str = "system",
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new tracking event for a parcel"""
        container = self.database.get_container_client(self.tracking_events_container)

        event = {
            "id": str(uuid.uuid4()),
            "barcode": barcode,
            "event_type": event_type,
            "location": location,
            "description": description,
            "scanned_by": scanned_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "additional_info": additional_info or {},
        }

        try:
            created_event = await container.create_item(body=event)
            return created_event
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error creating tracking event: {e}")
            raise

    async def get_parcel_tracking_history(self, barcode: str) -> List[Dict[str, Any]]:
        """Get all tracking events for a parcel (searches by barcode, tracking_number, or id)"""
        container = self.database.get_container_client(self.tracking_events_container)

        try:
            # Search across multiple identifier fields
            items = container.query_items(
                query="""SELECT * FROM c
                         WHERE c.barcode = @identifier
                         OR c.tracking_number = @identifier
                         OR c.id = @identifier
                         ORDER BY c.timestamp DESC""",
                parameters=[{"name": "@identifier", "value": barcode}],
            )
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving tracking history: {e}")
            return []

    # ==================== APPROVAL WORKFLOW ====================

    async def request_approval(
        self,
        parcel_barcode: str,
        request_type: str,
        description: str,
        priority: str = "medium",
        requested_by: str = "system",
        parcel_dc: str = None,
        parcel_status: str = None,
    ) -> str:
        """Request supervisor approval for logistics operations"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        request_id = str(uuid.uuid4())
        approval_request = {
            "id": request_id,
            "parcel_barcode": parcel_barcode,
            "request_type": request_type,
            "description": description,
            "priority": priority,
            "requested_by": requested_by,
            "status": "pending",
            "request_timestamp": datetime.now(timezone.utc).isoformat(),
            "approved_by": None,
            "approval_timestamp": None,
            "comments": None,
            "barcode": parcel_barcode,  # For partition key
            "parcel_dc": parcel_dc,
            "parcel_status": parcel_status,
        }

        try:
            await container.create_item(body=approval_request)
            print(f"✅ Approval request created: {request_id}")
            return request_id
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error creating approval request: {e}")
            raise

    async def get_approval_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a supervisor approval request"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.id = @request_id",
                parameters=[{"name": "@request_id", "value": request_id}],
            )
            requests = [item async for item in items]
            return requests[0] if requests else None
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving approval status: {e}")
            return None

    async def get_all_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.status = 'pending' AND IS_DEFINED(c.request_type)"
            )
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving pending approvals: {e}")
            return []

    async def get_all_approved_items(self) -> List[Dict[str, Any]]:
        """Get all approved requests"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        try:
            items = container.query_items(query="SELECT * FROM c WHERE c.status = 'approved'")
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving approved items: {e}")
            return []

    async def approve_request(self, request_id: str, approved_by: str, comments: Optional[str] = None) -> bool:
        """Approve a pending request"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        try:
            # Get the request
            request = await self.get_approval_status(request_id)
            if not request:
                print(f"❌ Approval request not found: {request_id}")
                return False

            # Update the request
            request["status"] = "approved"
            request["approved_by"] = approved_by
            request["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
            request["comments"] = comments

            await container.replace_item(item=request, body=request)
            print(f"✅ Request approved: {request_id} by {approved_by}")
            return True

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error approving request: {e}")
            return False

    async def reject_request(self, request_id: str, rejected_by: str, comments: Optional[str] = None) -> bool:
        """Reject a pending request"""
        container = self.database.get_container_client(self.delivery_attempts_container)

        try:
            # Get the request
            request = await self.get_approval_status(request_id)
            if not request:
                print(f"❌ Approval request not found: {request_id}")
                return False

            # Update the request
            request["status"] = "rejected"
            request["approved_by"] = rejected_by
            request["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
            request["comments"] = comments

            await container.replace_item(item=request, body=request)
            print(f"✅ Request rejected: {request_id} by {rejected_by}")
            return True

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error rejecting request: {e}")
            return False

    # ==================== FEEDBACK MANAGEMENT ====================

    async def store_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """Store customer feedback in Cosmos DB"""
        container = self.database.get_container_client(self.feedback_container)

        try:
            feedback_id = str(uuid.uuid4())
            feedback_record = {
                "id": feedback_id,
                "tracking_number": feedback_data["tracking_number"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nps_score": feedback_data["nps_score"],
                "nps_category": feedback_data["nps_category"],
                "delivery_time_rating": feedback_data["delivery_time_rating"],
                "courier_service_rating": feedback_data["courier_service_rating"],
                "parcel_condition_rating": feedback_data["parcel_condition_rating"],
                "overall_satisfaction": feedback_data["overall_satisfaction"],
                "additional_comments": feedback_data.get("additional_comments", ""),
                "customer_id": feedback_data.get("customer_id"),
                "feedback_type": "post_delivery",
            }

            await container.create_item(body=feedback_record)
            print(f"✅ Feedback stored successfully: {feedback_id}")
            return feedback_id

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error storing feedback: {e}")
            return None

    async def get_feedback_by_tracking(self, tracking_number: str) -> List[Dict[str, Any]]:
        """Get all feedback for a specific tracking number"""
        container = self.database.get_container_client(self.feedback_container)

        try:
            query = "SELECT * FROM c WHERE c.tracking_number = @tracking_number ORDER BY c.timestamp DESC"
            items = container.query_items(query=query, parameters=[("@tracking_number", tracking_number)])

            return [item async for item in items]

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving feedback: {e}")
            return []

    async def get_recent_feedback(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent feedback within specified days"""
        container = self.database.get_container_client(self.feedback_container)

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            query = "SELECT * FROM c WHERE c.timestamp >= @cutoff_date ORDER BY c.timestamp DESC"
            items = container.query_items(query=query, parameters=[("@cutoff_date", cutoff_iso)])

            return [item async for item in items]

        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving recent feedback: {e}")
            return []

    async def get_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback analytics and NPS metrics"""
        recent_feedback = await self.get_recent_feedback(days)

        if not recent_feedback:
            return {
                "total_responses": 0,
                "average_nps": 0,
                "nps_distribution": {"promoters": 0, "passives": 0, "detractors": 0},
                "average_ratings": {},
            }

        # Calculate metrics
        total_responses = len(recent_feedback)
        nps_scores = [f["nps_score"] for f in recent_feedback if "nps_score" in f]

        promoters = len([s for s in nps_scores if s >= 9])
        passives = len([s for s in nps_scores if 7 <= s <= 8])
        detractors = len([s for s in nps_scores if s <= 6])

        # NPS calculation: (% Promoters) - (% Detractors)
        nps = ((promoters - detractors) / total_responses * 100) if total_responses > 0 else 0

        # Average ratings
        delivery_ratings = [f["delivery_time_rating"] for f in recent_feedback if "delivery_time_rating" in f]
        courier_ratings = [f["courier_service_rating"] for f in recent_feedback if "courier_service_rating" in f]
        condition_ratings = [f["parcel_condition_rating"] for f in recent_feedback if "parcel_condition_rating" in f]
        overall_ratings = [f["overall_satisfaction"] for f in recent_feedback if "overall_satisfaction" in f]

        return {
            "total_responses": total_responses,
            "nps_score": round(nps, 1),
            "average_nps": round(sum(nps_scores) / len(nps_scores), 1) if nps_scores else 0,
            "nps_distribution": {"promoters": promoters, "passives": passives, "detractors": detractors},
            "average_ratings": {
                "delivery_time": round(sum(delivery_ratings) / len(delivery_ratings), 1) if delivery_ratings else 0,
                "courier_service": round(sum(courier_ratings) / len(courier_ratings), 1) if courier_ratings else 0,
                "parcel_condition": round(sum(condition_ratings) / len(condition_ratings), 1)
                if condition_ratings
                else 0,
                "overall_satisfaction": round(sum(overall_ratings) / len(overall_ratings), 1) if overall_ratings else 0,
            },
            "period_days": days,
        }

    # ==================== COMPANY INFORMATION MANAGEMENT ====================

    async def store_company_info(self, info_type: str, info_data: Dict[str, Any]) -> str:
        """Store company information in Cosmos DB"""
        try:
            info_id = f"company_{info_type}_{uuid.uuid4().hex[:8]}"

            company_info = {
                "id": info_id,
                "info_type": info_type,
                "data": info_data,
                "created_timestamp": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            container = self.database.get_container_client(self.company_info_container)
            await container.create_item(body=company_info)

            return info_id
        except Exception as e:
            print(f"❌ Error storing company information: {e}")
            return None

    async def get_company_info(self, info_type: str) -> List[Dict[str, Any]]:
        """Retrieve company information by type"""
        try:
            container = self.database.get_container_client(self.company_info_container)

            query = "SELECT * FROM c WHERE c.info_type = @info_type ORDER BY c.created_timestamp DESC"
            parameters = [{"name": "@info_type", "value": info_type}]

            items = []
            async for item in container.query_items(query=query, parameters=parameters, partition_key=info_type):
                items.append(item)

            return items
        except Exception as e:
            print(f"❌ Error retrieving company information: {e}")
            return []

    async def update_company_info(self, info_id: str, info_type: str, new_data: Dict[str, Any]) -> bool:
        """Update existing company information"""
        try:
            container = self.database.get_container_client(self.company_info_container)

            # Get existing item
            existing_item = await container.read_item(item=info_id, partition_key=info_type)

            # Update data and timestamp
            existing_item["data"] = new_data
            existing_item["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Replace the item
            await container.replace_item(item=info_id, body=existing_item)

            return True
        except Exception as e:
            print(f"❌ Error updating company information: {e}")
            return False

    async def get_latest_company_info(self, info_type: str) -> Optional[Dict[str, Any]]:
        """Get the most recent company information of a specific type"""
        company_info = await self.get_company_info(info_type)
        return company_info[0] if company_info else None

    # ==================== SUSPICIOUS MESSAGE REPORTS ====================

    async def store_suspicious_message(
        self,
        message_content: str,
        sender_info: str,
        risk_indicators: List[str] = None,
        ai_analysis: Dict[str, Any] = None,
    ) -> str:
        """Store suspicious message report in Cosmos DB with optional AI analysis"""
        try:
            report_id = f"suspicious_{uuid.uuid4().hex[:8]}"
            report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            suspicious_report = {
                "id": report_id,
                "report_date": report_date,
                "message_content": message_content,
                "sender_info": sender_info,
                "risk_indicators": risk_indicators or [],
                "ai_analysis": ai_analysis or {},
                "status": "pending_review",
                "reported_timestamp": datetime.now(timezone.utc).isoformat(),
                "review_timestamp": None,
                "reviewer": None,
                "resolution": None,
            }

            container = self.database.get_container_client(self.suspicious_messages_container)
            await container.create_item(body=suspicious_report)

            return report_id
        except Exception as e:
            print(f"❌ Error storing suspicious message report: {e}")
            return None

    async def get_suspicious_messages(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get suspicious message reports from the last N days"""
        try:
            container = self.database.get_container_client(self.suspicious_messages_container)

            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime("%Y-%m-%d")

            query = """
                SELECT * FROM c
                WHERE c.report_date >= @start_date
                ORDER BY c.reported_timestamp DESC
            """
            parameters = [{"name": "@start_date", "value": start_date_str}]

            items = []
            async for item in container.query_items(query=query, parameters=parameters):
                items.append(item)

            return items
        except Exception as e:
            print(f"❌ Error retrieving suspicious messages: {e}")
            return []

    async def get_pending_suspicious_reports(self) -> List[Dict[str, Any]]:
        """Get all suspicious message reports pending review"""
        try:
            container = self.database.get_container_client(self.suspicious_messages_container)

            query = "SELECT * FROM c WHERE c.status = 'pending_review' ORDER BY c.reported_timestamp DESC"

            items = []
            async for item in container.query_items(query=query):
                items.append(item)

            return items
        except Exception as e:
            print(f"❌ Error retrieving pending suspicious reports: {e}")
            return []

    async def update_suspicious_message_status(
        self, report_id: str, status: str, reviewer: str, resolution: str = None
    ) -> bool:
        """Update the status of a suspicious message report"""
        try:
            container = self.database.get_container_client(self.suspicious_messages_container)

            # First get the item to find its partition key
            query = "SELECT * FROM c WHERE c.id = @report_id"
            parameters = [{"name": "@report_id", "value": report_id}]

            items = []
            async for item in container.query_items(query=query, parameters=parameters):
                items.append(item)

            if not items:
                print(f"❌ Suspicious message report {report_id} not found")
                return False

            existing_item = items[0]

            # Update the item
            existing_item["status"] = status
            existing_item["reviewer"] = reviewer
            existing_item["resolution"] = resolution
            existing_item["review_timestamp"] = datetime.now(timezone.utc).isoformat()

            # Replace the item
            await container.replace_item(item=report_id, body=existing_item)

            return True
        except Exception as e:
            print(f"❌ Error updating suspicious message status: {e}")
            return False

    async def get_suspicious_message_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics on suspicious message reports"""
        try:
            messages = await self.get_suspicious_messages(days)

            if not messages:
                return {
                    "total_reports": 0,
                    "status_breakdown": {},
                    "risk_indicators_frequency": {},
                    "reports_by_day": {},
                    "period_days": days,
                }

            # Calculate analytics
            total_reports = len(messages)
            status_breakdown = {}
            risk_indicators_frequency = {}
            reports_by_day = {}

            for message in messages:
                # Status breakdown
                status = message.get("status", "unknown")
                status_breakdown[status] = status_breakdown.get(status, 0) + 1

                # Risk indicators frequency
                for indicator in message.get("risk_indicators", []):
                    risk_indicators_frequency[indicator] = risk_indicators_frequency.get(indicator, 0) + 1

                # Reports by day
                report_date = message.get("report_date", "unknown")
                reports_by_day[report_date] = reports_by_day.get(report_date, 0) + 1

            return {
                "total_reports": total_reports,
                "status_breakdown": status_breakdown,
                "risk_indicators_frequency": risk_indicators_frequency,
                "reports_by_day": reports_by_day,
                "period_days": days,
            }
        except Exception as e:
            print(f"❌ Error generating suspicious message analytics: {e}")
            return {}

    # ==================== DRIVER MANIFEST OPERATIONS ====================

    async def create_driver_manifest(
        self,
        driver_id: str,
        driver_name: str,
        parcel_barcodes: List[str],
        manifest_date: str = None,
        driver_state: str = None,
        driver_location: str = None,
        max_items: int = 150,
        reason: str = None,
    ) -> Optional[str]:
        """Create a delivery manifest for a driver with configurable max parcels (default 150)"""
        try:
            if len(parcel_barcodes) > max_items:
                print(f"⚠️ Warning: Manifest limited to {max_items} items. Truncating list.")
                parcel_barcodes = parcel_barcodes[:max_items]

            manifest_id = f"manifest_{driver_id}_{uuid.uuid4().hex[:8]}"
            manifest_date = manifest_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Get parcel details for each barcode and assign to driver
            parcels_container = self.database.get_container_client(self.parcels_container)
            manifest_items = []

            for barcode in parcel_barcodes:
                query = "SELECT * FROM c WHERE c.barcode = @barcode"
                parameters = [{"name": "@barcode", "value": barcode}]

                async for parcel in parcels_container.query_items(query=query, parameters=parameters):
                    # Update parcel with driver assignment and status
                    parcel["assigned_driver"] = driver_id
                    parcel["driver_name"] = driver_name
                    parcel["current_status"] = "in_transit"
                    parcel["manifest_id"] = manifest_id
                    parcel["assigned_timestamp"] = datetime.now(timezone.utc).isoformat()

                    # Update the parcel in the database
                    await parcels_container.upsert_item(body=parcel)

                    manifest_items.append(
                        {
                            "barcode": parcel.get("barcode"),
                            "recipient_name": parcel.get("recipient_name"),
                            "recipient_address": parcel.get("recipient_address"),
                            "recipient_phone": parcel.get("recipient_phone"),
                            "destination_state": parcel.get("destination_state"),
                            "destination_postcode": parcel.get("destination_postcode"),
                            "destination_city": parcel.get("destination_city"),
                            "status": parcel.get("current_status"),
                            "priority": parcel.get("priority", "normal"),
                            "delivery_notes": parcel.get("delivery_notes", ""),
                        }
                    )
                    break  # Only take first match

            manifest = {
                "id": manifest_id,
                "driver_id": driver_id,
                "driver_name": driver_name,
                "driver_state": driver_state or "NSW",
                "driver_location": driver_location or driver_state or "NSW",
                "manifest_date": manifest_date,
                "reason": reason or "",
                "items": manifest_items,
                "total_items": len(manifest_items),
                "completed_items": 0,
                "status": "active",
                "created_timestamp": datetime.now(timezone.utc).isoformat(),
                "route_optimized": False,
                "optimized_route": None,
                "estimated_duration_minutes": None,
                "estimated_distance_km": None,
            }

            # Store in database (using driver_id as partition key)
            container = self.database.get_container_client("driver_manifests")
            await container.create_item(body=manifest)

            print(f"✅ Created manifest {manifest_id} for driver {driver_name} with {len(manifest_items)} items")
            return manifest_id

        except Exception as e:
            print(f"❌ Error creating driver manifest: {e}")
            return None

    async def get_driver_manifest(self, driver_id: str, manifest_date: str = None) -> Optional[Dict[str, Any]]:
        """Get active manifest for a driver on a specific date"""
        try:
            container = self.database.get_container_client("driver_manifests")
            manifest_date = manifest_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # First try to get manifest for the specific date
            query = """
                SELECT * FROM c
                WHERE c.driver_id = @driver_id
                AND c.manifest_date = @date
                AND c.status = 'active'
            """
            parameters = [{"name": "@driver_id", "value": driver_id}, {"name": "@date", "value": manifest_date}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                return manifest  # Return first active manifest

            # If no manifest found for today, get the most recent active manifest
            query_fallback = """
                SELECT * FROM c
                WHERE c.driver_id = @driver_id
                AND c.status = 'active'
                ORDER BY c.manifest_date DESC
            """
            parameters_fallback = [{"name": "@driver_id", "value": driver_id}]

            async for manifest in container.query_items(query=query_fallback, parameters=parameters_fallback):
                print(f"📋 [DEBUG] Using fallback manifest dated {manifest.get('manifest_date')} for driver {driver_id}")
                return manifest  # Return most recent active manifest

            return None

        except Exception as e:
            print(f"❌ Error retrieving driver manifest: {e}")
            return None

    async def get_manifest_by_id(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """Get manifest by ID"""
        try:
            container = self.database.get_container_client("driver_manifests")
            query = "SELECT * FROM c WHERE c.id = @manifest_id"
            parameters = [{"name": "@manifest_id", "value": manifest_id}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                return manifest

            return None

        except Exception as e:
            print(f"❌ Error retrieving manifest by ID: {e}")
            return None

    async def update_manifest_route(
        self,
        manifest_id: str,
        optimized_route: List[Dict[str, Any]],
        estimated_duration: int,
        estimated_distance: float,
        is_optimized: bool = True,
        traffic_considered: bool = True,
        route_type: str = "fastest",
        all_routes: Dict[str, Any] = None,
    ) -> bool:
        """Update manifest with optimized route information

        Args:
            manifest_id: The manifest ID to update
            optimized_route: The waypoints for the selected route
            estimated_duration: Duration in minutes
            estimated_distance: Distance in km
            is_optimized: Whether route is optimized
            traffic_considered: Whether traffic was considered
            route_type: Type of route selected ('fastest', 'shortest', 'safest')
            all_routes: Dictionary containing all route options for driver selection
        """
        try:
            container = self.database.get_container_client("driver_manifests")

            # Get existing manifest
            query = "SELECT * FROM c WHERE c.id = @manifest_id"
            parameters = [{"name": "@manifest_id", "value": manifest_id}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                manifest["route_optimized"] = True
                manifest["optimized_route"] = optimized_route
                manifest["estimated_duration_minutes"] = estimated_duration
                manifest["estimated_distance_km"] = estimated_distance
                manifest["route_updated_timestamp"] = datetime.now(timezone.utc).isoformat()
                manifest["optimized"] = is_optimized
                manifest["traffic_considered"] = traffic_considered
                manifest["selected_route_type"] = route_type

                # Store all route options if provided
                if all_routes:
                    manifest["all_routes"] = all_routes  # Changed from route_options to all_routes
                    manifest["multi_route_enabled"] = True

                await container.replace_item(item=manifest_id, body=manifest)
                print(f"✅ Updated manifest {manifest_id} with {route_type} route")
                if all_routes:
                    print(f"   📊 Stored {len([k for k in all_routes.keys() if k != 'recommended'])} route options")
                return True

            print(f"⚠️ Manifest {manifest_id} not found")
            return False

        except Exception as e:
            print(f"❌ Error updating manifest route: {e}")
            return False

    async def update_driver_route_preference(self, manifest_id: str, route_type: str) -> bool:
        """Update the driver's selected route preference

        Args:
            manifest_id: The manifest ID
            route_type: The route type to switch to ('fastest', 'shortest', 'safest')
        """
        try:
            container = self.database.get_container_client("driver_manifests")

            # Get existing manifest
            query = "SELECT * FROM c WHERE c.id = @manifest_id"
            parameters = [{"name": "@manifest_id", "value": manifest_id}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                all_routes = manifest.get("all_routes") or {}

                if route_type not in all_routes or not all_routes[route_type].get("total_duration_minutes"):
                    print(f"❌ Route type '{route_type}' not calculated yet for manifest {manifest_id}")
                    return False

                selected_route = all_routes[route_type]

                # Update manifest with selected route
                manifest["selected_route_type"] = route_type
                manifest["optimized_route"] = selected_route.get("waypoints", [])
                manifest["estimated_duration_minutes"] = selected_route.get("total_duration_minutes", 0)
                manifest["estimated_distance_km"] = selected_route.get("total_distance_km", 0)
                manifest["route_preference_updated"] = datetime.now(timezone.utc).isoformat()

                await container.replace_item(item=manifest_id, body=manifest)
                print(f"✅ Updated manifest {manifest_id} to use {route_type} route")
                return True

            return False

        except Exception as e:
            print(f"❌ Error updating route preference: {e}")
            return False

    async def mark_delivery_complete(self, manifest_id: str, barcode: str, driver_note: str = None) -> bool:
        """Mark a delivery as complete in the manifest

        Args:
            manifest_id: The manifest ID
            barcode: The parcel barcode
            driver_note: Optional note from driver about this delivery/address
        """
        try:
            container = self.database.get_container_client("driver_manifests")

            # Get existing manifest
            query = "SELECT * FROM c WHERE c.id = @manifest_id"
            parameters = [{"name": "@manifest_id", "value": manifest_id}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                # Update item status
                delivery_address = None
                for item in manifest["items"]:
                    if item["barcode"] == barcode:
                        item["status"] = "delivered"
                        item["delivered_timestamp"] = datetime.now(timezone.utc).isoformat()
                        if driver_note:
                            item["driver_note"] = driver_note
                        delivery_address = item.get("recipient_address")

                # Save address note for future deliveries if provided
                if driver_note and delivery_address:
                    await self.save_address_note(delivery_address, driver_note, manifest.get("driver_name", "Unknown"))

                # Update counters
                manifest["completed_items"] = sum(1 for item in manifest["items"] if item.get("status") == "delivered")

                # Check if all complete
                if manifest["completed_items"] == manifest["total_items"]:
                    manifest["status"] = "completed"
                    manifest["completed_timestamp"] = datetime.now(timezone.utc).isoformat()

                await container.replace_item(item=manifest_id, body=manifest)
                return True

            return False

        except Exception as e:
            print(f"❌ Error marking delivery complete: {e}")
            return False

    # ── Address note categories & TTL ──────────────────────────────────
    # Notes are auto-categorised at save time. Each category has a retention period
    # after which notes are automatically filtered out on read and pruned.
    NOTE_CATEGORIES = {
        "carded": {
            "ttl_days": 30,
            "label": "Carded",
            "keywords": [
                "card left",
                "carded",
                "no one home",
                "not home",
                "no answer",
                "not available",
                "collect from",
                "recipient not available",
                "left card",
            ],
        },
        "safety": {
            "ttl_days": 180,
            "label": "Safety",
            "keywords": [
                "dog",
                "dogs",
                "aggressive",
                "dangerous",
                "weapon",
                "unsafe",
                "caution",
                "beware",
                "threat",
                "attack",
                "bitten",
                "bite",
                "guard dog",
                "loose animal",
                "hostile",
                "violent",
                "intimidat",
            ],
        },
        "access": {
            "ttl_days": 180,
            "label": "Access",
            "keywords": [
                "gate",
                "code",
                "pin",
                "buzzer",
                "intercom",
                "side entrance",
                "rear entrance",
                "back door",
                "key",
                "lockbox",
                "concierge",
                "reception",
                "loading dock",
                "lift",
                "elevator",
                "floor",
                "unit",
                "apartment",
                "level",
            ],
        },
        "property": {
            "ttl_days": 180,
            "label": "Property",
            "keywords": [
                "broken",
                "doorbell",
                "bell",
                "stairs",
                "steps",
                "steep",
                "driveway",
                "narrow",
                "no parking",
                "gravel",
                "mud",
                "flood",
                "overgrown",
            ],
        },
    }
    # Fallback for notes that don't match any category
    DEFAULT_NOTE_TTL_DAYS = 90

    @staticmethod
    def _categorise_note(note_text: str) -> tuple:
        """Categorise a note based on keyword matching.

        Returns:
            (category_key, ttl_days)
        """
        text_lower = note_text.lower()
        for cat_key, cat_info in ParcelTrackingDB.NOTE_CATEGORIES.items():
            for keyword in cat_info["keywords"]:
                if keyword in text_lower:
                    return cat_key, cat_info["ttl_days"]
        return "general", ParcelTrackingDB.DEFAULT_NOTE_TTL_DAYS

    async def save_address_note(self, address: str, note: str, driver_name: str) -> bool:
        """Save or append a note about a delivery address for future reference.

        Notes are auto-categorised (carded / safety / access / property / general)
        and given an expiry date based on category TTL rules.

        Args:
            address: The delivery address
            note: The note to save
            driver_name: Name of the driver who added the note
        """
        try:
            container = self.database.get_container_client("address_notes")

            # Normalize address for consistent lookups
            normalized_address = address.strip().lower()
            note_id = f"note_{normalized_address.replace(' ', '_').replace(',', '')}"

            # Auto-categorise and calculate expiry
            category, ttl_days = self._categorise_note(note)
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(days=ttl_days)).isoformat()

            new_entry = {
                "note_id": uuid.uuid4().hex[:12],
                "note": note,
                "driver_name": driver_name,
                "timestamp": now.isoformat(),
                "category": category,
                "ttl_days": ttl_days,
                "expires_at": expires_at,
            }

            # Check if document already exists for this address
            query = "SELECT * FROM c WHERE c.normalized_address = @address"
            parameters = [{"name": "@address", "value": normalized_address}]

            existing_doc = None
            async for doc in container.query_items(query=query, parameters=parameters):
                existing_doc = doc
                break

            if existing_doc:
                existing_doc["notes"].append(new_entry)
                existing_doc["last_updated"] = now.isoformat()
                await container.replace_item(item=existing_doc["id"], body=existing_doc)
                print(f"✅ Updated address note for {address} (category: {category}, expires: {ttl_days}d)")
            else:
                note_doc = {
                    "id": note_id,
                    "address": address,
                    "normalized_address": normalized_address,
                    "notes": [new_entry],
                    "created_at": now.isoformat(),
                    "last_updated": now.isoformat(),
                }
                await container.create_item(body=note_doc)
                print(f"✅ Created new address note for {address} (category: {category}, expires: {ttl_days}d)")

            return True

        except Exception as e:
            print(f"❌ Error saving address note: {e}")
            # Don't fail the delivery if note saving fails
            return False

    async def get_address_notes(self, address: str) -> List[Dict[str, Any]]:
        """Get all *active* (non-expired) notes for a specific delivery address.

        Expired notes are filtered out on read. If any expired notes are found,
        they are lazily pruned from the document to keep the store clean.

        Args:
            address: The delivery address to look up

        Returns:
            List of active notes with driver name, timestamp, category, and expires_at
        """
        try:
            container = self.database.get_container_client("address_notes")

            # Normalize address for lookup
            normalized_address = address.strip().lower()

            query = "SELECT * FROM c WHERE c.normalized_address = @address"
            parameters = [{"name": "@address", "value": normalized_address}]

            now = datetime.now(timezone.utc)

            async for doc in container.query_items(query=query, parameters=parameters):
                all_notes = doc.get("notes", [])

                # Separate active vs expired notes
                active_notes = []
                pruned = False
                for n in all_notes:
                    expires_at_str = n.get("expires_at")
                    if expires_at_str:
                        try:
                            expires_at = datetime.fromisoformat(expires_at_str)
                            if expires_at <= now:
                                pruned = True
                                continue  # Skip expired note
                        except (ValueError, TypeError):
                            pass  # Keep notes with unparseable expiry
                    # Legacy notes without expires_at are kept (will be categorised on next save)
                    active_notes.append(n)

                # Lazy prune: write back if we removed any expired notes
                if pruned:
                    try:
                        doc["notes"] = active_notes
                        doc["last_updated"] = now.isoformat()
                        if active_notes:
                            await container.replace_item(item=doc["id"], body=doc)
                        else:
                            # No notes left – delete the document entirely
                            await container.delete_item(item=doc["id"], partition_key=normalized_address)
                            print(f"🗑️ Deleted empty address notes document for {address}")
                    except Exception as prune_err:
                        # Non-critical – don't fail the read
                        if os.getenv("DEBUG_MODE") == "True":
                            print(f"⚠️ Lazy prune failed for {address}: {prune_err}")

                return active_notes

            return []

        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                return []
            print(f"❌ Error retrieving address notes: {e}")
            return []
        except Exception as e:
            if os.getenv("DEBUG_MODE") == "True":
                print(f"❌ Error retrieving address notes: {e}")
            return []

    async def dismiss_address_note(self, address: str, note_id: str, dismissed_by: str) -> bool:
        """Dismiss (delete) a specific note that is no longer accurate.

        Drivers can remove stale notes (e.g. after a property changes owners).

        Args:
            address: The delivery address
            note_id: The unique note_id of the note entry to remove
            dismissed_by: Username/name of the driver dismissing the note

        Returns:
            True if the note was found and removed
        """
        try:
            container = self.database.get_container_client("address_notes")
            normalized_address = address.strip().lower()

            query = "SELECT * FROM c WHERE c.normalized_address = @address"
            parameters = [{"name": "@address", "value": normalized_address}]

            async for doc in container.query_items(query=query, parameters=parameters):
                original_count = len(doc.get("notes", []))
                doc["notes"] = [n for n in doc.get("notes", []) if n.get("note_id") != note_id]

                if len(doc["notes"]) == original_count:
                    return False  # Note not found

                doc["last_updated"] = datetime.now(timezone.utc).isoformat()

                if doc["notes"]:
                    await container.replace_item(item=doc["id"], body=doc)
                else:
                    await container.delete_item(item=doc["id"], partition_key=normalized_address)

                print(f"🗑️ Note {note_id} dismissed by {dismissed_by} for {address}")
                return True

            return False

        except Exception as e:
            print(f"❌ Error dismissing address note: {e}")
            return False

    async def get_all_active_manifests(self) -> List[Dict[str, Any]]:
        """Get all active manifests for admin overview"""
        try:
            container = self.database.get_container_client("driver_manifests")

            query = "SELECT * FROM c WHERE c.status = 'active' ORDER BY c.created_timestamp DESC"

            manifests = []
            async for manifest in container.query_items(query=query):
                manifests.append(manifest)

            return manifests

        except Exception as e:
            print(f"❌ Error retrieving active manifests: {e}")
            return []

    async def get_manifest_for_parcel(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Get the active manifest containing a specific parcel"""
        try:
            container = self.database.get_container_client("driver_manifests")
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            # Query for active manifests that contain this parcel
            query = """
                SELECT * FROM c
                WHERE c.manifest_date = @date
                AND c.status = 'active'
                AND ARRAY_CONTAINS(c.items, {'barcode': @barcode}, true)
            """
            parameters = [{"name": "@date", "value": today}, {"name": "@barcode", "value": barcode}]

            async for manifest in container.query_items(query=query, parameters=parameters):
                return manifest  # Return first match

            return None

        except Exception as e:
            print(f"❌ Error retrieving manifest for parcel: {e}")
            return None

    # ==================== STORE-SPECIFIC OPERATIONS ====================

    async def get_parcels_by_store(self, store_location: str) -> List[Dict[str, Any]]:
        """Get all parcels for a specific store - leverages partition key for efficient queries"""
        container = self.database.get_container_client(self.parcels_container)

        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.store_location = @store",
                parameters=[{"name": "@store", "value": store_location}],
                partition_key=store_location,
            )
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcels for store {store_location}: {e}")
            return []

    async def get_store_statistics(self, store_location: str) -> Dict[str, Any]:
        """Get statistics for a specific store"""
        parcels = await self.get_parcels_by_store(store_location)

        stats = {
            "store_location": store_location,
            "total_parcels": len(parcels),
            "status_breakdown": {},
            "service_type_breakdown": {},
            "recent_registrations": 0,
            "pending_deliveries": 0,
            "completed_deliveries": 0,
        }

        # Calculate statistics
        now = datetime.now(timezone.utc)
        for parcel in parcels:
            # Status breakdown
            status = parcel.get("current_status", "unknown")
            stats["status_breakdown"][status] = stats["status_breakdown"].get(status, 0) + 1

            # Service type breakdown
            service = parcel.get("service_type", "unknown")
            stats["service_type_breakdown"][service] = stats["service_type_breakdown"].get(service, 0) + 1

            # Recent registrations (last 24 hours)
            reg_time = datetime.fromisoformat(parcel["registration_timestamp"].replace("Z", "+00:00"))
            if (now - reg_time).days < 1:
                stats["recent_registrations"] += 1

            # Delivery status
            if parcel.get("is_delivered"):
                stats["completed_deliveries"] += 1
            elif status in ["out_for_delivery", "at_depot", "in_transit"]:
                stats["pending_deliveries"] += 1

        return stats

    # ==================== UTILITY FUNCTIONS ====================

    def _generate_tracking_number(self) -> str:
        """Generate a tracking number for parcels"""
        # Format: 2 letter prefix + 8 digits + 2 letter suffix
        prefixes = ["LP", "EX", "RG", "OV"]  # LastPost, Express, Regular, Overnight
        prefix = random.choice(prefixes)
        numbers = "".join([str(random.randint(0, 9)) for _ in range(8)])
        suffix = "".join([string.ascii_uppercase[random.randint(0, 25)] for _ in range(2)])
        return f"{prefix}{numbers}{suffix}"

    def _calculate_estimated_delivery(self, service_type: str) -> str:
        """Calculate estimated delivery date based on service type"""
        base_date = datetime.now(timezone.utc)

        if service_type == "overnight":
            delivery_date = base_date + timedelta(days=1)
        elif service_type == "express":
            delivery_date = base_date + timedelta(days=2)
        elif service_type == "registered":
            delivery_date = base_date + timedelta(days=4)
        else:  # standard
            delivery_date = base_date + timedelta(days=5)

        return delivery_date.isoformat()

    # ==================== TEST DATA AND SETUP ====================

    async def add_random_test_parcels(self, count: int = 5) -> List[Dict[str, Any]]:
        """Add random test parcels for logistics testing"""
        parcels = []
        # Import real GNAF-verified address pool
        import sys as _sys
        _gen_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "generators")
        if _gen_dir not in _sys.path:
            _sys.path.insert(0, _gen_dir)
        from real_addresses import pick_real_address
        service_types = ["standard", "express", "overnight", "registered"]

        # Distribution centers (matching the 40 from approvals page)
        distribution_centers = [
            "DC-SYD-001",
            "DC-SYD-002",
            "DC-SYD-003",
            "DC-MEL-001",
            "DC-MEL-002",
            "DC-MEL-003",
            "DC-BNE-001",
            "DC-BNE-002",
            "DC-BNE-003",
            "DC-PER-001",
            "DC-PER-002",
            "DC-ADL-001",
            "DC-ADL-002",
            "DC-CAN-001",
            "DC-HOB-001",
            "DC-DAR-001",
            "DC-NEW-001",
            "DC-WOL-001",
            "DC-GEE-001",
            "DC-BAL-001",
            "DC-GLD-001",
            "DC-TWD-001",
            "DC-CAI-001",
            "DC-TOW-001",
            "DC-LAU-001",
            "DC-BEN-001",
            "DC-ALB-001",
            "DC-WAG-001",
            "DC-TRA-001",
            "DC-SHP-001",
            "DC-BUN-001",
            "DC-GER-001",
            "DC-KAL-001",
            "DC-MOU-001",
            "DC-WHY-001",
            "DC-POR-001",
            "DC-DUB-001",
            "DC-TAM-001",
            "DC-ARM-001",
            "DC-ROC-001",
        ]

        # Parcel statuses with realistic progression
        status_options = [
            {"status": "Registered", "location": "Store"},
            {"status": "Collected", "location": "In Transit"},
            {"status": "At Depot", "location": "Distribution Center"},
            {"status": "Sorting", "location": "Sorting Facility"},
            {"status": "In Transit", "location": "On Route"},
            {"status": "Out for Delivery", "location": "Delivery Vehicle"},
            {"status": "Delivered", "location": "Recipient Address"},
        ]

        # Australian postcodes and states mapping (expanded VIC range)
        postcode_state_mapping = {
            "2000": "NSW",
            "2007": "NSW",
            "2010": "NSW",
            "3000": "VIC",
            "3004": "VIC",
            "3141": "VIC",
            "3181": "VIC",
            "3182": "VIC",
            "4000": "QLD",
            "4006": "QLD",
            "4101": "QLD",
            "5000": "SA",
            "5006": "SA",
            "6000": "WA",
            "6008": "WA",
            "7000": "TAS",
            "7001": "TAS",
            "0200": "ACT",
            "2600": "ACT",
        }
        postcode_city_mapping = {
            "2000": "Sydney", "2007": "Sydney", "2010": "Sydney",
            "3000": "Melbourne", "3004": "Melbourne", "3141": "Melbourne",
            "3181": "Melbourne", "3182": "Melbourne",
            "4000": "Brisbane", "4006": "Brisbane", "4101": "Brisbane",
            "5000": "Adelaide", "5006": "Adelaide",
            "6000": "Perth", "6008": "Perth",
            "7000": "Hobart", "7001": "Hobart",
            "0200": "Canberra", "2600": "Canberra",
        }
        postcodes = list(postcode_state_mapping.keys())

        # Australian store locations
        store_locations = [
            "Store_Sydney_CBD",
            "Store_Melbourne_CBD",
            "Store_Brisbane_CBD",
            "Store_Adelaide_CBD",
            "Store_Perth_CBD",
        ]

        for _ in range(count):
            postcode = random.choice(postcodes)
            state = postcode_state_mapping[postcode]
            city = postcode_city_mapping[postcode]
            store = random.choice(store_locations)
            status_info = random.choice(status_options)

            # Distribution center assignment based on parcel status:
            # - 'Registered': Just logged at post office, DC not yet assigned
            # - 'Collected': Picked up but not at DC yet
            # - 'Out for Delivery': Has left DC system, now with local delivery
            # - 'Delivered': Delivery complete, DC processing finished
            # - All other statuses (At Depot, Sorting, In Transit): Active in DC system
            if status_info["status"] == "Registered":
                dc = "To Be Advised"
            elif status_info["status"] in ["Out for Delivery", "Delivered"]:
                dc = "Completed"
            elif status_info["status"] == "Collected":
                dc = "Unknown DC"
            else:
                # Parcels at depot, sorting, or in transit get actual DC assignments
                dc = random.choice(distribution_centers)

            # Create parcel with correct status and DC from the start (no update needed)
            parcel = await self.register_parcel(
                barcode=fake.ean13(),
                sender_name=fake.name(),
                sender_address=pick_real_address(state, city)[0],
                sender_phone=fake.phone_number(),
                recipient_name=fake.name(),
                recipient_address=pick_real_address(state, city)[0],
                recipient_phone=fake.phone_number(),
                destination_postcode=postcode,
                destination_state=state,
                service_type=random.choice(service_types),
                weight=round(random.uniform(0.1, 25.0), 2),
                dimensions=f"{random.randint(10,50)}x{random.randint(10,50)}x{random.randint(5,30)}cm",
                declared_value=round(random.uniform(10, 500), 2),
                store_location=store,
                # NEW: Set status and DC at creation time
                current_status=status_info["status"],
                origin_location=dc,
                current_location=(
                    dc if status_info["status"] in ["At Depot", "Sorting"]
                    else f"{dc} - {status_info['location']}" if status_info["status"] == "In Transit"
                    else status_info["location"]
                ),
                fraud_risk_score=random.randint(0, 100),
            )

            # Generate realistic parcel history based on current status
            try:
                await self._generate_parcel_history(parcel["barcode"], status_info["status"], dc, store)
            except Exception as e:
                print(f"Warning: Could not generate history for {parcel['barcode']}: {e}")

            parcels.append(parcel)

        return parcels

    async def _generate_parcel_history(self, barcode: str, current_status: str, dc: str, store: str):
        """Generate realistic tracking history based on parcel's current status"""

        # Define the progression stages with time delays (in hours)
        history_stages = [
            {"status": "Registered", "location": store, "description": "Parcel registered and lodged", "hours_ago": 72},
            {
                "status": "Collected",
                "location": "Collection Point",
                "description": "Parcel collected for transit",
                "hours_ago": 68,
            },
            {
                "status": "In Transit",
                "location": "En Route to Sorting Center",
                "description": "In transit to sorting facility",
                "hours_ago": 60,
            },
            {"status": "At Depot", "location": f"{dc}", "description": f"Arrived at {dc}", "hours_ago": 48},
            {
                "status": "Sorting",
                "location": f"{dc} Sorting Facility",
                "description": "Parcel being sorted",
                "hours_ago": 46,
            },
            {
                "status": "In Transit",
                "location": f"{dc} - Distribution Hub",
                "description": "In transit to distribution center",
                "hours_ago": 36,
            },
            {
                "status": "Out for Delivery",
                "location": "Delivery Vehicle",
                "description": "Out for delivery with courier",
                "hours_ago": 4,
            },
            {
                "status": "Delivered",
                "location": "Recipient Address",
                "description": "Parcel successfully delivered",
                "hours_ago": 1,
            },
        ]

        # Determine which stages to include based on current status
        status_index = {
            "Registered": 0,
            "Collected": 1,
            "At Depot": 3,
            "Sorting": 4,
            "In Transit": 5,
            "Out for Delivery": 6,
            "Delivered": 7,
        }

        end_index = status_index.get(current_status, 0)

        # Create tracking events for each stage up to current status
        for i in range(end_index + 1):
            stage = history_stages[i]
            event_time = datetime.now(timezone.utc) - timedelta(hours=stage["hours_ago"])

            try:
                container = self.database.get_container_client(self.tracking_events_container)
                event = {
                    "id": str(uuid.uuid4()),
                    "barcode": barcode,
                    "event_type": "status_update",
                    "location": stage["location"],
                    "description": stage["description"],
                    "scanned_by": "system"
                    if i == 0
                    else random.choice(["Driver-A", "Handler-B", "Sorter-C", "Courier-D"]),
                    "timestamp": event_time.isoformat(),
                    "additional_info": {"status": stage["status"], "scan_type": "automated" if i < 2 else "manual"},
                }
                await container.create_item(body=event)
            except Exception as e:
                print(f"Warning: Could not create tracking event for {barcode}: {e}")

    async def add_random_approval_requests(self, count: int = 3) -> List[str]:
        """Add random approval requests for logistics operations"""
        request_ids = []
        request_types = [
            "exception_handling",
            "return_to_sender",
            "delivery_redirect",
            "damage_claim",
            "lost_package",
            "delivery_confirmation",
        ]
        priorities = ["low", "medium", "high", "critical"]

        # Get some existing parcels
        all_parcels = await self.get_all_parcels()
        if not all_parcels:
            # Create some test parcels first
            all_parcels = await self.add_random_test_parcels(5)

        # Filter out parcels with invalid DCs (only use parcels actively in DC system)
        parcels = [
            p
            for p in all_parcels
            if p.get("origin_location") and p.get("origin_location") not in ["Unknown DC", "To Be Advised", "Completed"]
        ]

        if not parcels:
            print("⚠️  No parcels with valid DCs found for approval requests")
            return []

        for _ in range(count):
            parcel = random.choice(parcels)
            request_type = random.choice(request_types)
            priority = random.choice(priorities)

            # Get DC and status info from parcel
            dc_info = parcel.get("origin_location", "Unknown DC")
            status_info = parcel.get("current_status", "unknown")

            description = f"{request_type.replace('_', ' ').title()} for parcel {parcel['barcode']}"

            # Add verification flags for testing auto-approval
            if random.random() > 0.7:
                description += " - Verified sender"

            request_id = await self.request_approval(
                parcel_barcode=parcel["barcode"],
                request_type=request_type,
                description=description,
                priority=priority,
                requested_by=fake.name(),
                parcel_dc=dc_info,
                parcel_status=status_info,
            )
            request_ids.append(request_id)

        return request_ids

    async def cleanup_approval_requests(self) -> bool:
        """Clean up all approval requests from the database

        NOTE: These items appear in queries but cannot be read or deleted.
        They are phantom/stale results that don't actually exist in the container.
        This is likely due to:
        1. Test data created with invalid barcodes (e.g., 'TEST123')
        2. Items that don't match the partition key they claim to have
        3. Query cache showing items that were already deleted

        Since these items can't be interacted with, we just report success.
        """
        print("⚠️  Approval request cleanup skipped - items are phantom query results")
        print("    These items show in queries but don't actually exist in the database")
        print("    This is a known issue with test data created outside normal workflows")
        return True

    async def cleanup_database(self, confirm: bool = False):
        """Clean up all data from the database"""
        if not confirm:
            print("⚠️  This will delete ALL data from the database!")
            print("Call with confirm=True to proceed")
            return False

        containers = [self.parcels_container, self.tracking_events_container, self.delivery_attempts_container]

        for container_name in containers:
            try:
                container = self.database.get_container_client(container_name)
                items = container.query_items(query="SELECT c.id, c.barcode FROM c")

                deleted_count = 0
                async for item in items:
                    try:
                        # Use barcode as partition key for tracking_events and delivery_attempts
                        # Use store_location for parcels, but we need to get it first
                        if container_name == self.parcels_container:
                            # For parcels, we need the full item to get store_location
                            full_item = await container.read_item(
                                item=item["id"], partition_key=item.get("store_location", "unknown")
                            )
                            await container.delete_item(
                                item=item["id"], partition_key=full_item.get("store_location", "unknown")
                            )
                        else:
                            # For other containers, use barcode as partition key
                            await container.delete_item(item=item["id"], partition_key=item.get("barcode", "unknown"))
                        deleted_count += 1
                    except Exception as e:
                        print(f"Error deleting item {item['id']}: {e}")

                print(f"✅ Deleted {deleted_count} items from {container_name}")

            except Exception as e:
                print(f"❌ Error cleaning up container {container_name}: {e}")

        return True

    # ==================== ADDRESS HISTORY METHODS ====================

    def normalize_address(self, address: str) -> str:
        """
        Normalize an address for consistent matching
        Removes extra spaces, standardizes case, removes unit numbers for matching
        """
        if not address:
            return ""

        # Convert to lowercase and strip
        normalized = address.lower().strip()

        # Remove common variations
        normalized = normalized.replace(",", " ")
        normalized = " ".join(normalized.split())  # Remove extra spaces

        # Standardize state abbreviations
        state_map = {
            "new south wales": "nsw",
            "victoria": "vic",
            "queensland": "qld",
            "south australia": "sa",
            "western australia": "wa",
            "tasmania": "tas",
            "northern territory": "nt",
            "australian capital territory": "act",
        }

        for full_name, abbrev in state_map.items():
            normalized = normalized.replace(full_name, abbrev)

        return normalized

    async def add_address_delivery(
        self, address: str, parcel_barcode: str, recipient_name: str, sender_name: str = None, notes: str = None
    ) -> dict:
        """
        Add a delivery record to an address's history
        Creates or updates the address history document

        Args:
            address: Delivery address
            parcel_barcode: Barcode of the parcel being delivered
            recipient_name: Name of recipient
            sender_name: Name of sender (optional)
            notes: Any notes about this delivery (optional)

        Returns:
            Updated address history document
        """
        container = self.database.get_container_client(self.address_history_container)
        address_normalized = self.normalize_address(address)

        # Try to get existing address history
        try:
            query = f"SELECT * FROM c WHERE c.address_normalized = @address"
            parameters = [{"name": "@address", "value": address_normalized}]

            items = []
            async for item in container.query_items(
                query=query, parameters=parameters, partition_key=address_normalized
            ):
                items.append(item)

            if items:
                # Update existing history
                address_doc = items[0]
            else:
                # Create new address history document
                address_doc = {
                    "id": str(uuid.uuid4()),
                    "address_normalized": address_normalized,
                    "address_display": address,
                    "first_delivery_date": datetime.now(timezone.utc).isoformat(),
                    "deliveries": [],
                    "total_deliveries": 0,
                    "notes": [],
                }
        except Exception:
            # Create new document
            address_doc = {
                "id": str(uuid.uuid4()),
                "address_normalized": address_normalized,
                "address_display": address,
                "first_delivery_date": datetime.now(timezone.utc).isoformat(),
                "deliveries": [],
                "total_deliveries": 0,
                "notes": [],
            }

        # Add new delivery record
        delivery_record = {
            "parcel_barcode": parcel_barcode,
            "recipient_name": recipient_name,
            "sender_name": sender_name,
            "delivery_date": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }

        address_doc["deliveries"].append(delivery_record)
        address_doc["total_deliveries"] = len(address_doc["deliveries"])
        address_doc["last_delivery_date"] = datetime.now(timezone.utc).isoformat()

        # Add general notes if provided
        if notes:
            address_doc["notes"].append(
                {"note": notes, "date": datetime.now(timezone.utc).isoformat(), "parcel_barcode": parcel_barcode}
            )

        # Upsert the document
        result = await container.upsert_item(address_doc)
        return result

    async def get_address_history(self, address: str) -> Optional[dict]:
        """
        Get complete delivery history for an address

        Args:
            address: Address to look up

        Returns:
            Address history document with all deliveries and notes, or None if not found
        """
        container = self.database.get_container_client(self.address_history_container)
        address_normalized = self.normalize_address(address)

        try:
            query = f"SELECT * FROM c WHERE c.address_normalized = @address"
            parameters = [{"name": "@address", "value": address_normalized}]

            async for item in container.query_items(
                query=query, parameters=parameters, partition_key=address_normalized
            ):
                return item

            return None
        except Exception as e:
            print(f"Error getting address history: {e}")
            return None

    async def add_address_note(self, address: str, note: str) -> bool:
        """
        Add a general note to an address (not tied to a specific parcel)

        Args:
            address: Address to add note to
            note: Note text

        Returns:
            True if successful, False otherwise
        """
        container = self.database.get_container_client(self.address_history_container)
        address_normalized = self.normalize_address(address)

        try:
            # Get existing address history
            address_doc = await self.get_address_history(address)

            if not address_doc:
                # Create new address document if it doesn't exist
                address_doc = {
                    "id": str(uuid.uuid4()),
                    "address_normalized": address_normalized,
                    "address_display": address,
                    "first_delivery_date": datetime.now(timezone.utc).isoformat(),
                    "deliveries": [],
                    "total_deliveries": 0,
                    "notes": [],
                }

            # Add the note
            address_doc["notes"].append(
                {"note": note, "date": datetime.now(timezone.utc).isoformat(), "parcel_barcode": None}
            )

            # Update the document
            await container.upsert_item(address_doc)
            return True

        except Exception as e:
            print(f"Error adding address note: {e}")
            return False

    # ==================== SYNCHRONOUS WRAPPERS ====================

    def get_all_scanned_items_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_all_parcels (backward compatibility)"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error retrieving scanned items: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.get_all_parcels() instead")
                return []
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._run_async_get_all_parcels())
                finally:
                    # Cleanup the event loop properly
                    loop.close()
        except Exception as e:
            print(f"❌ Error retrieving scanned items: {e}")
            return []

    async def _run_async_get_all_parcels(self):
        async with self:
            return await self.get_all_parcels()

    def add_scanned_item_sync(
        self, barcode: str, item_name: str, sender_name: str, recipient_name: str, recipient_address: str
    ) -> Dict[str, Any]:
        """Synchronous wrapper for register_parcel (backward compatibility)"""
        # Extract postcode from address (simple extraction)
        address_parts = recipient_address.split(",")
        postcode = address_parts[-1].strip() if address_parts else "UNKNOWN"

        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error adding scanned item: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.register_parcel() instead")
                return {}
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self._run_async_register_parcel(
                            barcode, item_name, sender_name, recipient_name, recipient_address, postcode
                        )
                    )
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error adding scanned item: {e}")
            return {}

    async def _run_async_register_parcel(
        self, barcode, item_name, sender_name, recipient_name, recipient_address, postcode
    ):
        async with self:
            return await self.register_parcel(
                barcode=barcode,
                sender_name=sender_name,
                sender_address="N/A",
                sender_phone=None,
                recipient_name=recipient_name,
                recipient_address=recipient_address,
                recipient_phone=None,
                destination_postcode=postcode,
                destination_state="NSW",  # Default
                service_type="standard",
                store_location="Store_Default",
            )

    def request_human_approval_sync(self, item_barcode: str, request_type: str, description: str) -> str:
        """Synchronous wrapper for request_approval"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error requesting approval: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.request_approval() instead")
                return "error"
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self._run_async_request_approval(item_barcode, request_type, description)
                    )
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error requesting approval: {e}")
            return "error"

    async def _run_async_request_approval(self, item_barcode, request_type, description):
        async with self:
            return await self.request_approval(item_barcode, request_type, description)

    def get_all_pending_approvals_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_all_pending_approvals"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error retrieving pending approvals: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.get_all_pending_approvals() instead")
                return []
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._run_async_get_pending_approvals())
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error retrieving pending approvals: {e}")
            return []

    async def _run_async_get_pending_approvals(self):
        async with self:
            return await self.get_all_pending_approvals()

    def get_all_approved_items_sync(self) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_all_approved_items"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error retrieving approved items: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.get_all_approved_items() instead")
                return []
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._run_async_get_approved_items())
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error retrieving approved items: {e}")
            return []

    async def _run_async_get_approved_items(self):
        async with self:
            return await self.get_all_approved_items()

    def approve_request_sync(self, request_id: str, approved_by: str, comments: Optional[str] = None) -> bool:
        """Synchronous wrapper for approve_request"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error approving request: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.approve_request() instead")
                return False
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._run_async_approve_request(request_id, approved_by, comments))
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error approving request: {e}")
            return False

    async def _run_async_approve_request(self, request_id, approved_by, comments):
        async with self:
            return await self.approve_request(request_id, approved_by, comments)

    def reject_request_sync(self, request_id: str, rejected_by: str, comments: Optional[str] = None) -> bool:
        """Synchronous wrapper for reject_request"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error rejecting request: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.reject_request() instead")
                return False
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._run_async_reject_request(request_id, rejected_by, comments))
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error rejecting request: {e}")
            return False

    async def _run_async_reject_request(self, request_id, rejected_by, comments):
        async with self:
            return await self.reject_request(request_id, rejected_by, comments)

    async def get_available_drivers(self, state: str = None) -> List[Dict[str, Any]]:
        """Get list of available drivers for manifest assignment

        Args:
            state: Optional filter by driver's state (e.g., 'VIC', 'NSW')

        Returns:
            List of driver dictionaries with id, name, and location
        """
        try:
            # For now, return hardcoded drivers based on user database
            # In production, this would query a drivers table/container
            container = self.database.get_container_client("users")
            query = "SELECT * FROM c WHERE c.role = 'driver'"

            drivers = []
            async for user in container.query_items(query=query):
                driver_info = {
                    "driver_id": user.get("username"),
                    "name": user.get("full_name", user.get("username")),
                    "location": user.get("state", "VIC"),
                    "max_capacity": 20,
                    "current_load": 0,  # Would calculate from active manifests
                }

                # Filter by state if provided
                if state is None or driver_info["location"] == state:
                    drivers.append(driver_info)

            print(f"✅ Found {len(drivers)} available drivers")
            return drivers

        except Exception as e:
            print(f"❌ Error getting available drivers: {e}")
            return []

    async def get_user_state(self, username: str) -> str:
        """Get a user's state from the users container

        Args:
            username: The username/driver_id to look up

        Returns:
            The user's state (e.g., 'VIC', 'NSW') or 'NSW' as default
        """
        try:
            container = self.database.get_container_client("users")
            query = "SELECT c.state FROM c WHERE c.username = @username"
            parameters = [{"name": "@username", "value": username}]

            async for user in container.query_items(query=query, parameters=parameters):
                return user.get("state", "NSW")

            # If user not found, return default
            return "NSW"

        except Exception as e:
            print(f"❌ Error getting user state for {username}: {e}")
            return "NSW"

    async def get_pending_parcels(
        self, status: str = "at_depot", max_count: int = None, state: str = None
    ) -> List[Dict[str, Any]]:
        """Get parcels that are pending manifest assignment

        Args:
            status: Parcel status to filter by (default: 'at_depot')
            max_count: Optional maximum number of parcels to return
            state: Optional filter by delivery state (e.g., 'VIC', 'NSW')

        Returns:
            List of parcel dictionaries ready for manifest assignment
        """
        try:
            container = self.database.get_container_client(self.parcels_container)

            # Build query with optional state filter
            if state:
                query = """
                    SELECT * FROM c
                    WHERE LOWER(c.current_status) = LOWER(@status)
                    AND (NOT IS_DEFINED(c.assigned_driver) OR c.assigned_driver = null)
                    AND c.recipient_state = @state
                    ORDER BY c.registration_timestamp DESC
                """
                parameters = [{"name": "@status", "value": status}, {"name": "@state", "value": state}]
            else:
                query = """
                    SELECT * FROM c
                    WHERE LOWER(c.current_status) = LOWER(@status)
                    AND (NOT IS_DEFINED(c.assigned_driver) OR c.assigned_driver = null)
                    ORDER BY c.registration_timestamp DESC
                """
                parameters = [{"name": "@status", "value": status}]

            parcels = []
            async for parcel in container.query_items(query=query, parameters=parameters):
                parcels.append(parcel)

                if max_count and len(parcels) >= max_count:
                    break

            state_msg = f" in {state}" if state else ""
            print(f"✅ Found {len(parcels)} pending parcels with status '{status}'{state_msg}")
            return parcels

        except Exception as e:
            print(f"❌ Error getting pending parcels: {e}")
            return []

    def scan_parcel_at_location_sync(
        self, barcode: str, scan_location: str, scanned_by: str = "system", scan_type: str = "arrival"
    ) -> Dict[str, Any]:
        """Synchronous wrapper for scan_parcel_at_location"""
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we can't use run_until_complete
                print("❌ Error scanning parcel: Cannot run the event loop while another loop is running")
                print("💡 Use async version: await db.scan_parcel_at_location() instead")
                return {"success": False, "error": "Event loop conflict"}
            except RuntimeError:
                # No running loop, safe to create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(
                        self._run_async_scan_parcel_at_location(barcode, scan_location, scanned_by, scan_type)
                    )
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error scanning parcel: {e}")
            return {"success": False, "error": str(e)}

    async def _run_async_scan_parcel_at_location(self, barcode, scan_location, scanned_by, scan_type):
        async with self:
            return await self.scan_parcel_at_location(barcode, scan_location, scanned_by, scan_type)


# ==================== CONVENIENCE FUNCTIONS ====================


def get_database_interface() -> ParcelTrackingDB:
    """
    Get the database interface

    Returns:
        ParcelTrackingDB instance
    """
    return ParcelTrackingDB()


# ==================== SETUP AND TESTING ====================


async def initialize_company_information():
    """Initialize company information with Zava data"""
    print("=== Initializing Company Information ===")

    async with ParcelTrackingDB() as db:
        # Company profile information
        company_profile = {
            "company_name": "Zava",
            "company_type": "Logistics and Courier Services",
            "founded": "2025",
            "headquarters": "Australia",
            "services": [
                "Last Mile Delivery",
                "Parcel Tracking",
                "Package Collection",
                "Express Delivery",
                "Store Pickup Services",
            ],
        }

        # Security and fraud prevention policies
        security_policies = {
            "fraud_prevention": {
                "never_requests": [
                    "Payment via text message",
                    "Personal details in unsolicited messages",
                    "Actions through non-official domains",
                    "Immediate action for failed deliveries",
                ],
                "contact_methods": [
                    "Official customer service phone line",
                    "Official website contact forms",
                    "In-person at authorized pickup locations",
                ],
            }
        }

        # Customer service information
        customer_service = {
            "contact_policy": "For genuine delivery issues, contact customer service directly",
            "official_domains": ["dtlogistics.com.au"],
            "customer_service_hours": "Monday-Friday 8AM-6PM, Saturday 9AM-4PM",
            "emergency_contact": "Available 24/7 for urgent delivery issues",
        }

        # Store company information
        profile_id = await db.store_company_info("company_profile", company_profile)
        security_id = await db.store_company_info("security_policies", security_policies)
        service_id = await db.store_company_info("customer_service", customer_service)

        if profile_id and security_id and service_id:
            print("✅ Company information initialized successfully")
            print(f"   📋 Company Profile ID: {profile_id}")
            print(f"   🔒 Security Policies ID: {security_id}")
            print(f"   📞 Customer Service ID: {service_id}")
            return True
        else:
            print("❌ Failed to initialize company information")
            return False


async def setup_database_with_test_data():
    """Setup database with initial test data"""
    print("=== Setting up Database with Test Data ===")

    # Check environment variables
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    key = os.getenv("COSMOS_DB_KEY")

    if not endpoint or not key:
        print("ERROR: COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set")
        print("Please update your .env file with your Cosmos DB credentials")
        return False

    print(f"Cosmos DB Endpoint: {endpoint}")
    print(f"Database Name: {os.getenv('COSMOS_DB_DATABASE_NAME', 'agent_workflow_db')}")

    try:
        async with ParcelTrackingDB() as db:
            # Add some initial test data
            print("\n=== Generating Test Parcels ===")
            test_parcels = await db.add_random_test_parcels(30)
            print(f"Added {len(test_parcels)} test parcels")

            # Display the parcels
            parcels = await db.get_all_parcels()
            for parcel in parcels:
                print(
                    f"- {parcel['barcode']}: {parcel['recipient_name']} ({parcel['destination_postcode']}) - {parcel['service_type']}"
                )

            # Add some approval requests
            print("\n=== Adding Test Approval Requests ===")
            approval_requests = await db.add_random_approval_requests(10)
            print(f"Added {len(approval_requests)} approval requests")

            # Display pending approvals
            pending = await db.get_all_pending_approvals()
            for approval in pending:
                print(f"- Request {approval['id']}: {approval['description']} (Priority: {approval['priority']})")

            # Initialize company information
            print("\n=== Initializing Company Information ===")
            company_init_success = await initialize_company_information()
            if not company_init_success:
                print("⚠️  Company information initialization failed")

            print("\n=== Database Setup Complete ===")
            return True

    except Exception as e:
        print(f"Error setting up database: {e}")
        return False


async def test_approval_workflow():
    """Test the approval workflow"""
    print("\n=== Testing Approval Workflow ===")

    try:
        async with ParcelTrackingDB() as db:
            # Get all parcels
            parcels = await db.get_all_parcels()
            if not parcels:
                print("No parcels found. Adding some test parcels first...")
                await db.add_random_test_parcels(3)
                parcels = await db.get_all_parcels()

            # Create an approval request for the first parcel
            if parcels:
                parcel = parcels[0]
                print(f"Creating approval request for parcel: {parcel['barcode']} - To: {parcel['recipient_name']}")

                request_id = await db.request_approval(
                    parcel_barcode=parcel["barcode"],
                    request_type="delivery_redirect",
                    description=f"Request delivery redirect for parcel to {parcel['recipient_name']}",
                    priority="high",
                )

                print(f"Created approval request: {request_id}")

                # Check the approval status
                status = await db.get_approval_status(request_id)
                print(f"Initial status: {status['status']}")

                # Approve the request
                approved = await db.approve_request(request_id, "test_supervisor", "Approved for testing")
                if approved:
                    print("Request approved successfully")

                    # Check final status
                    final_status = await db.get_approval_status(request_id)
                    print(f"Final status: {final_status['status']} by {final_status['approved_by']}")

    except Exception as e:
        print(f"Error testing approval workflow: {e}")


async def display_database_contents():
    """Display all database contents"""
    print("\n=== Current Database Contents ===")

    try:
        async with ParcelTrackingDB() as db:
            # Display parcels
            print("\n--- Parcels ---")
            parcels = await db.get_all_parcels()
            if parcels:
                for i, parcel in enumerate(parcels, 1):
                    print(f"{i}. Barcode: {parcel['barcode']}")
                    print(f"   Tracking: {parcel['tracking_number']}")
                    print(f"   From: {parcel['sender_name']}")
                    print(f"   To: {parcel['recipient_name']} ({parcel['destination_postcode']})")
                    print(f"   Service: {parcel['service_type']}")
                    print(f"   Status: {parcel['current_status']}")
                    print(f"   Location: {parcel['current_location']}")
                    print(f"   Registered: {parcel['registration_timestamp']}")
                    if parcel.get("special_instructions"):
                        print(f"   Special: {parcel['special_instructions']}")
                    print()
            else:
                print("No parcels found")

            # Display pending approvals
            print("--- Pending Approvals ---")
            pending = await db.get_all_pending_approvals()
            if pending:
                for i, approval in enumerate(pending, 1):
                    print(f"{i}. Request ID: {approval['id']}")
                    print(f"   Parcel: {approval['parcel_barcode']}")
                    print(f"   Type: {approval['request_type']}")
                    print(f"   Description: {approval['description']}")
                    print(f"   Priority: {approval['priority']}")
                    print(f"   Requested: {approval['request_timestamp']}")
                    print()
            else:
                print("No pending approvals found")

    except Exception as e:
        print(f"Error displaying database contents: {e}")


async def cleanup_all_data():
    """Clean up all data from the database"""
    print("\n=== Cleaning up database ===")
    try:
        async with ParcelTrackingDB() as db:
            await db.cleanup_database(confirm=True)
            print("Database cleaned up successfully")
    except Exception as e:
        print(f"Error cleaning up database: {e}")


async def main():
    """Main function to run setup and tests"""
    print("Parcel Tracking Database - Setup and Testing")
    print("=" * 50)

    while True:
        print("\nOptions:")
        print("1. Generate test data")
        print("2. Test approval workflow")
        print("3. Display database contents")
        print("4. Clean up all data")
        print("5. Exit")

        choice = input("\nEnter your choice (1-5): ")

        if choice == "1":
            await setup_database_with_test_data()
        elif choice == "2":
            await test_approval_workflow()
        elif choice == "3":
            await display_database_contents()
        elif choice == "4":
            confirm = input("Are you sure you want to delete all data? (yes/no): ")
            if confirm.lower() == "yes":
                await cleanup_all_data()
        elif choice == "5":
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    asyncio.run(main())
