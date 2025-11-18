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

import os
import uuid
import random
import string
import asyncio
import warnings
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Suppress aiohttp warnings for cleaner output
warnings.filterwarnings("ignore", message="Unclosed client session")
warnings.filterwarnings("ignore", message="Unclosed connector")
warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed")

# Azure imports
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions, PartitionKey
from azure.identity.aio import DefaultAzureCredential, AzureCliCredential

# Test data generation
from faker import Faker

# Load environment variables
load_dotenv()

# Initialize Faker for generating test data with Australian locale
fake = Faker('en_AU')


class ParcelTrackingDB:
    """Consolidated Parcel Tracking Database Interface"""
    
    def __init__(self):
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "agent_workflow_db")
        
        # Container names
        self.parcels_container = "parcels"
        self.tracking_events_container = "tracking_events"
        self.delivery_attempts_container = "delivery_attempts"
        self.feedback_container = "feedback"
        self.company_info_container = "company_info"
        self.suspicious_messages_container = "suspicious_messages"
        
        # Connection objects
        self.client = None
        self.database = None
        self.credential = None

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
                raise ValueError("COSMOS_DB_ENDPOINT environment variable is required")
            
            # Try key-based authentication first, fall back to Azure AD if it fails
            auth_successful = False
            
            if self.key:
                try:
                    # Use key-based authentication
                    self.client = CosmosClient(self.endpoint, self.key)
                    # Silently test the connection
                    
                    # Test the connection by attempting to access the database
                    self.database = await self.client.create_database_if_not_exists(
                        id=self.database_name,
                        offer_throughput=400
                    )
                    auth_successful = True
                    
                except Exception as key_error:
                    if "Local Authorization is disabled" in str(key_error) or "Unauthorized" in str(key_error):
                        # Silently switch to Azure AD authentication
                        auth_successful = False
                    else:
                        raise key_error
            
            if not auth_successful:
                # Use Azure credential authentication
                self.credential = DefaultAzureCredential()
                self.client = CosmosClient(self.endpoint, self.credential)
                # Silently connect using Azure credentials
                
                # Get or create database (serverless - no throughput)
                self.database = await self.client.create_database_if_not_exists(
                    id=self.database_name
                )
            # Create containers if they don't exist
            await self._create_containers()
            
            # Database connection successful - ready for operations
            
        except Exception as e:
            print(f"❌ Failed to connect to Cosmos DB: {e}")
            raise

    async def _create_containers(self):
        """Create containers with appropriate partition keys"""
        containers = [
            {
                "id": self.parcels_container,
                "partition_key": PartitionKey(path="/store_location"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            },
            {
                "id": self.tracking_events_container,
                "partition_key": PartitionKey(path="/barcode"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            },
            {
                "id": self.delivery_attempts_container,
                "partition_key": PartitionKey(path="/barcode"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            },
            {
                "id": self.feedback_container,
                "partition_key": PartitionKey(path="/tracking_number"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            },
            {
                "id": self.company_info_container,
                "partition_key": PartitionKey(path="/info_type"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            },
            {
                "id": self.suspicious_messages_container,
                "partition_key": PartitionKey(path="/report_date"),
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/*"}
                    ]
                }
            }
        ]
        
        for container_spec in containers:
            try:
                await self.database.create_container_if_not_exists(
                    id=container_spec["id"],
                    partition_key=container_spec["partition_key"],
                    indexing_policy=container_spec["indexing_policy"]
                )
                # Container ready - operations can proceed
                pass
            except Exception as e:
                # Container creation failed - continue with error
                raise

    async def close(self):
        """Close database connections and cleanup resources"""
        try:
            if self.client:
                # Properly close the aiohttp client session
                if hasattr(self.client, '_client_connection'):
                    try:
                        await self.client._client_connection.close()
                    except Exception:
                        pass
                
                # Close the Cosmos client
                if hasattr(self.client, 'close'):
                    try:
                        result = self.client.close()
                        # If it returns a coroutine, await it
                        if hasattr(result, '__await__'):
                            await result
                        # Add small delay to ensure cleanup completes
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
                self.client = None
            
            if self.credential:
                # Close Azure credentials properly
                if hasattr(self.credential, 'close') and callable(getattr(self.credential, 'close')):
                    try:
                        if asyncio.iscoroutinefunction(self.credential.close):
                            await self.credential.close()
                        else:
                            self.credential.close()
                        # Add delay for credential cleanup
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
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
        service_type: str = "standard",
        weight: Optional[float] = None,
        dimensions: Optional[str] = None,
        declared_value: Optional[float] = None,
        special_instructions: Optional[str] = None,
        store_location: str = "unknown"
    ) -> Dict[str, Any]:
        """Register a new parcel into the logistics network"""
        container = self.database.get_container_client(self.parcels_container)
        
        # Generate tracking number
        tracking_number = self._generate_tracking_number()
        
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
            "service_type": service_type,
            "weight": weight,
            "dimensions": dimensions,
            "declared_value": declared_value,
            "special_instructions": special_instructions,
            "store_location": store_location,
            "registration_timestamp": datetime.now(timezone.utc).isoformat(),
            "current_status": "registered",
            "current_location": store_location,
            "estimated_delivery": self._calculate_estimated_delivery(service_type),
            "delivery_attempts": 0,
            "is_delivered": False
        }
        
        try:
            created_parcel = await container.create_item(body=parcel)
            print(f"✅ Parcel registered: {barcode} → {tracking_number}")
            
            # Create initial tracking event
            await self.create_tracking_event(
                barcode=barcode,
                event_type="registered",
                location=store_location,
                description=f"Parcel registered for {recipient_name}"
            )
            
            return created_parcel
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error registering parcel: {e}")
            raise

    async def get_all_parcels(self) -> List[Dict[str, Any]]:
        """Get all parcels in the system"""
        container = self.database.get_container_client(self.parcels_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c"
            )
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcels: {e}")
            return []

    async def get_parcel_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """Get a specific parcel by barcode"""
        container = self.database.get_container_client(self.parcels_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.barcode = @barcode",
                parameters=[{"name": "@barcode", "value": barcode}]
            )
            parcels = [item async for item in items]
            return parcels[0] if parcels else None
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcel by barcode: {e}")
            return None

    async def get_parcel_by_tracking_number(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Get a specific parcel by tracking number"""
        container = self.database.get_container_client(self.parcels_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.tracking_number = @tracking",
                parameters=[{"name": "@tracking", "value": tracking_number}]
            )
            parcels = [item async for item in items]
            return parcels[0] if parcels else None
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving parcel by tracking number: {e}")
            return None

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
            
            if status == "delivered":
                parcel["is_delivered"] = True
                parcel["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            await container.replace_item(item=parcel, body=parcel)
            
            # Create tracking event
            await self.create_tracking_event(
                barcode=barcode,
                event_type=status,
                location=location,
                description=f"Parcel status updated to {status}",
                scanned_by=scanned_by
            )
            
            print(f"✅ Parcel status updated: {barcode} → {status}")
            return True
            
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error updating parcel status: {e}")
            return False

    async def scan_parcel_at_location(
        self, 
        barcode: str, 
        scan_location: str, 
        scanned_by: str = "system",
        scan_type: str = "arrival"
    ) -> Dict[str, Any]:
        """
        Smart location-aware parcel scanning that updates status and location based on scan location
        
        Args:
            barcode: Parcel barcode
            scan_location: Where the parcel was scanned (e.g., "Depot_Melbourne", "Store_Sydney_CBD", "Vehicle_001")
            scanned_by: Who scanned it
            scan_type: Type of scan - "arrival", "departure", "processing", "loading"
        
        Returns:
            Dictionary with scan result and updated parcel info
        """
        try:
            container = self.database.get_container_client(self.parcels_container)
            
            # Find the parcel
            parcel = await self.get_parcel_by_barcode(barcode)
            if not parcel:
                return {
                    "success": False,
                    "error": f"Parcel not found: {barcode}",
                    "scan_location": scan_location
                }
            
            # Determine new status and location based on scan location and current status
            current_status = parcel.get("current_status", "registered")
            current_location = parcel.get("current_location", "unknown")
            
            # Smart status determination based on scan location
            new_status, description = self._determine_status_from_location(
                scan_location, current_status, scan_type
            )
            
            # Update parcel location and status
            parcel["current_status"] = new_status
            parcel["current_location"] = scan_location
            parcel["last_updated"] = datetime.now(timezone.utc).isoformat()
            parcel["last_scanned_by"] = scanned_by
            parcel["last_scan_type"] = scan_type
            
            # Handle delivery completion
            if new_status == "delivered":
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
                    "transition": f"{current_location} → {scan_location}"
                }
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
                "timestamp": parcel["last_updated"]
            }
            
        except exceptions.CosmosHttpResponseError as e:
            return {
                "success": False,
                "error": f"Database error: {e}",
                "barcode": barcode,
                "scan_location": scan_location
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
                "barcode": barcode,
                "scan_location": scan_location
            }

    def _determine_status_from_location(self, scan_location: str, current_status: str, scan_type: str) -> tuple[str, str]:
        """
        Determine the appropriate status based on scan location, current status, and scan type
        
        Returns:
            Tuple of (new_status, description)
        """
        scan_location_lower = scan_location.lower()
        
        # Store scanning (initial registration or return)
        if "store" in scan_location_lower:
            if current_status == "registered":
                return "in_transit", f"Parcel collected from store and in transit to depot"
            else:
                return "at_store", f"Parcel scanned at {scan_location}"
        
        # Depot/Facility scanning
        elif any(keyword in scan_location_lower for keyword in ["depot", "facility", "warehouse", "sorting"]):
            if scan_type == "arrival":
                return "at_depot", f"Parcel arrived at {scan_location} for sorting and processing"
            elif scan_type == "departure":
                return "in_transit", f"Parcel departed {scan_location} for delivery route"
            elif scan_type == "processing":
                return "at_depot", f"Parcel being processed at {scan_location}"
            else:
                return "at_depot", f"Parcel scanned at {scan_location}"
        
        # Vehicle scanning (delivery truck, van, etc.)
        elif any(keyword in scan_location_lower for keyword in ["vehicle", "truck", "van", "delivery"]):
            if scan_type == "loading":
                return "out_for_delivery", f"Parcel loaded onto {scan_location} for delivery"
            elif scan_type == "arrival":
                return "out_for_delivery", f"Parcel on {scan_location} approaching destination"
            else:
                return "out_for_delivery", f"Parcel on {scan_location}"
        
        # Customer location scanning (delivery completion)
        elif any(keyword in scan_location_lower for keyword in ["customer", "recipient", "address", "delivery"]):
            return "delivered", f"Parcel delivered to customer at {scan_location}"
        
        # Hub scanning (major sorting/distribution centers)
        elif any(keyword in scan_location_lower for keyword in ["hub", "distribution", "center"]):
            if scan_type == "arrival":
                return "at_depot", f"Parcel arrived at distribution hub {scan_location}"
            elif scan_type == "departure":
                return "in_transit", f"Parcel departed distribution hub {scan_location}"
            else:
                return "at_depot", f"Parcel at distribution hub {scan_location}"
        
        # Default case - generic location
        else:
            if scan_type == "arrival":
                return "in_transit", f"Parcel arrived at {scan_location}"
            elif scan_type == "departure":
                return "in_transit", f"Parcel departed {scan_location}"
            else:
                return "in_transit", f"Parcel scanned at {scan_location}"

    # ==================== TRACKING EVENTS ====================

    async def create_tracking_event(
        self,
        barcode: str,
        event_type: str,
        location: str,
        description: str,
        scanned_by: str = "system",
        additional_info: Optional[Dict[str, Any]] = None
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
            "additional_info": additional_info or {}
        }
        
        try:
            created_event = await container.create_item(body=event)
            return created_event
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error creating tracking event: {e}")
            raise

    async def get_parcel_tracking_history(self, barcode: str) -> List[Dict[str, Any]]:
        """Get all tracking events for a parcel"""
        container = self.database.get_container_client(self.tracking_events_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.barcode = @barcode ORDER BY c.timestamp",
                parameters=[{"name": "@barcode", "value": barcode}],
                partition_key=barcode
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
        requested_by: str = "system"
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
            "barcode": parcel_barcode  # For partition key
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
                parameters=[{"name": "@request_id", "value": request_id}]
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
                query="SELECT * FROM c WHERE c.status = 'pending'"
            )
            return [item async for item in items]
        except exceptions.CosmosHttpResponseError as e:
            print(f"❌ Error retrieving pending approvals: {e}")
            return []

    async def get_all_approved_items(self) -> List[Dict[str, Any]]:
        """Get all approved requests"""
        container = self.database.get_container_client(self.delivery_attempts_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.status = 'approved'"
            )
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
                "feedback_type": "post_delivery"
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
            items = container.query_items(
                query=query,
                parameters=[("@tracking_number", tracking_number)],
                enable_cross_partition_query=True
            )
            
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
            items = container.query_items(
                query=query,
                parameters=[("@cutoff_date", cutoff_iso)],
                enable_cross_partition_query=True
            )
            
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
                "average_ratings": {}
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
            "nps_distribution": {
                "promoters": promoters,
                "passives": passives,
                "detractors": detractors
            },
            "average_ratings": {
                "delivery_time": round(sum(delivery_ratings) / len(delivery_ratings), 1) if delivery_ratings else 0,
                "courier_service": round(sum(courier_ratings) / len(courier_ratings), 1) if courier_ratings else 0,
                "parcel_condition": round(sum(condition_ratings) / len(condition_ratings), 1) if condition_ratings else 0,
                "overall_satisfaction": round(sum(overall_ratings) / len(overall_ratings), 1) if overall_ratings else 0
            },
            "period_days": days
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
                "last_updated": datetime.now(timezone.utc).isoformat()
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
            async for item in container.query_items(
                query=query,
                parameters=parameters,
                partition_key=info_type
            ):
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

    async def store_suspicious_message(self, message_content: str, sender_info: str, 
                                     risk_indicators: List[str] = None,
                                     ai_analysis: Dict[str, Any] = None) -> str:
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
                "resolution": None
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
            async for item in container.query_items(
                query=query,
                parameters=parameters
            ):
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
            async for item in container.query_items(
                query=query
            ):
                items.append(item)
            
            return items
        except Exception as e:
            print(f"❌ Error retrieving pending suspicious reports: {e}")
            return []

    async def update_suspicious_message_status(self, report_id: str, status: str, 
                                             reviewer: str, resolution: str = None) -> bool:
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
                    "period_days": days
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
                "period_days": days
            }
        except Exception as e:
            print(f"❌ Error generating suspicious message analytics: {e}")
            return {}

    # ==================== STORE-SPECIFIC OPERATIONS ====================

    async def get_parcels_by_store(self, store_location: str) -> List[Dict[str, Any]]:
        """Get all parcels for a specific store - leverages partition key for efficient queries"""
        container = self.database.get_container_client(self.parcels_container)
        
        try:
            items = container.query_items(
                query="SELECT * FROM c WHERE c.store_location = @store",
                parameters=[{"name": "@store", "value": store_location}],
                partition_key=store_location
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
            "completed_deliveries": 0
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
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        suffix = ''.join([string.ascii_uppercase[random.randint(0, 25)] for _ in range(2)])
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
        service_types = ["standard", "express", "overnight", "registered"]
        
        # Australian postcodes and states mapping (expanded VIC range)
        postcode_state_mapping = {
            "2000": "NSW", "2007": "NSW", "2010": "NSW",
            "3000": "VIC", "3004": "VIC", "3141": "VIC", "3181": "VIC", "3182": "VIC",
            "4000": "QLD", "4006": "QLD", "4101": "QLD",
            "5000": "SA", "5006": "SA",
            "6000": "WA", "6008": "WA",
            "7000": "TAS", "7001": "TAS",
            "0200": "ACT", "2600": "ACT"
        }
        postcodes = list(postcode_state_mapping.keys())
        
        # Australian store locations
        store_locations = ["Store_Sydney_CBD", "Store_Melbourne_CBD", "Store_Brisbane_CBD", "Store_Adelaide_CBD", "Store_Perth_CBD"]
        
        for _ in range(count):
            postcode = random.choice(postcodes)
            state = postcode_state_mapping[postcode]
            store = random.choice(store_locations)
            
            parcel = await self.register_parcel(
                barcode=fake.ean13(),
                sender_name=fake.name(),
                sender_address=fake.address(),
                sender_phone=fake.phone_number(),
                recipient_name=fake.name(),
                recipient_address=f"{fake.street_address()}, {fake.city()}, {state} {postcode}",
                recipient_phone=fake.phone_number(),
                destination_postcode=postcode,
                destination_state=state,
                service_type=random.choice(service_types),
                weight=round(random.uniform(0.1, 25.0), 2),
                dimensions=f"{random.randint(10,50)}x{random.randint(10,50)}x{random.randint(5,30)}cm",
                declared_value=round(random.uniform(10, 500), 2),
                store_location=store
            )
            parcels.append(parcel)
        
        return parcels

    async def add_random_approval_requests(self, count: int = 3) -> List[str]:
        """Add random approval requests for logistics operations"""
        request_ids = []
        request_types = ["exception_handling", "return_to_sender", "delivery_redirect", "damage_claim", "lost_package"]
        priorities = ["low", "medium", "high", "critical"]
        
        # Get some existing parcels
        parcels = await self.get_all_parcels()
        if not parcels:
            # Create some test parcels first
            parcels = await self.add_random_test_parcels(3)
        
        for _ in range(count):
            parcel = random.choice(parcels)
            request_type = random.choice(request_types)
            priority = random.choice(priorities)
            
            request_id = await self.request_approval(
                parcel_barcode=parcel["barcode"],
                request_type=request_type,
                description=f"{request_type.replace('_', ' ').title()} for parcel {parcel['barcode']}",
                priority=priority,
                requested_by=fake.name()
            )
            request_ids.append(request_id)
        
        return request_ids

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
                items = container.query_items(
                    query="SELECT c.id, c.barcode FROM c"
                )
                
                deleted_count = 0
                async for item in items:
                    try:
                        # Use barcode as partition key for tracking_events and delivery_attempts
                        # Use store_location for parcels, but we need to get it first
                        if container_name == self.parcels_container:
                            # For parcels, we need the full item to get store_location
                            full_item = await container.read_item(item=item["id"], partition_key=item.get("store_location", "unknown"))
                            await container.delete_item(item=item["id"], partition_key=full_item.get("store_location", "unknown"))
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

    def add_scanned_item_sync(self, barcode: str, item_name: str, sender_name: str, recipient_name: str, recipient_address: str) -> Dict[str, Any]:
        """Synchronous wrapper for register_parcel (backward compatibility)"""
        # Extract postcode from address (simple extraction)
        address_parts = recipient_address.split(',')
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
                    return loop.run_until_complete(self._run_async_register_parcel(
                        barcode, item_name, sender_name, recipient_name, recipient_address, postcode
                    ))
                finally:
                    loop.close()
        except Exception as e:
            print(f"❌ Error adding scanned item: {e}")
            return {}

    async def _run_async_register_parcel(self, barcode, item_name, sender_name, recipient_name, recipient_address, postcode):
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
                store_location="Store_Default"
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
                    return loop.run_until_complete(self._run_async_request_approval(item_barcode, request_type, description))
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

    def scan_parcel_at_location_sync(self, barcode: str, scan_location: str, scanned_by: str = "system", scan_type: str = "arrival") -> Dict[str, Any]:
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
                    return loop.run_until_complete(self._run_async_scan_parcel_at_location(barcode, scan_location, scanned_by, scan_type))
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
    """Initialize company information with DT Logistics data"""
    print("=== Initializing Company Information ===")
    
    async with ParcelTrackingDB() as db:
        # Company profile information
        company_profile = {
            "company_name": "DT Logistics",
            "company_type": "Logistics and Courier Services",
            "founded": "2025",
            "headquarters": "Australia",
            "services": [
                "Last Mile Delivery",
                "Parcel Tracking",
                "Package Collection",
                "Express Delivery",
                "Store Pickup Services"
            ]
        }
        
        # Security and fraud prevention policies
        security_policies = {
            "fraud_prevention": {
                "never_requests": [
                    "Payment via text message",
                    "Personal details in unsolicited messages",
                    "Actions through non-official domains",
                    "Immediate action for failed deliveries"
                ],
                "contact_methods": [
                    "Official customer service phone line",
                    "Official website contact forms",
                    "In-person at authorized pickup locations"
                ]
            }
        }
        
        # Customer service information
        customer_service = {
            "contact_policy": "For genuine delivery issues, contact customer service directly",
            "official_domains": ["dtlogistics.com.au"],
            "customer_service_hours": "Monday-Friday 8AM-6PM, Saturday 9AM-4PM",
            "emergency_contact": "Available 24/7 for urgent delivery issues"
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
            print("\n=== Adding Test Parcels ===")
            test_parcels = await db.add_random_test_parcels(5)
            print(f"Added {len(test_parcels)} test parcels")
            
            # Display the parcels
            parcels = await db.get_all_parcels()
            for parcel in parcels:
                print(f"- {parcel['barcode']}: {parcel['recipient_name']} ({parcel['destination_postcode']}) - {parcel['service_type']}")
            
            # Add some approval requests
            print("\n=== Adding Test Approval Requests ===")
            approval_requests = await db.add_random_approval_requests(3)
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
                    parcel_barcode=parcel['barcode'],
                    request_type="delivery_redirect",
                    description=f"Request delivery redirect for parcel to {parcel['recipient_name']}",
                    priority="high"
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
                    if parcel.get('special_instructions'):
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
        print("1. Setup database with test data")
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