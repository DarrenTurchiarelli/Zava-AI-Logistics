# Azure Cosmos DB tools for Last Mile Logistics Parcel Tracking
# This module provides functions to interact with Azure Cosmos DB for tracking parcels through the logistics network
# From store intake → sorting facility → driver pickup → delivery → customer handoff

import os
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from azure.cosmos.aio import CosmosClient
from azure.cosmos import exceptions, PartitionKey
import uuid
from faker import Faker
import random

# Initialize Faker for generating test data with Australian locale
fake = Faker('en_AU')

class CosmosDBManager:
    def __init__(self):
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE_NAME", "logistics_tracking_db")
        self.parcels_container = "parcels"
        self.tracking_events_container = "tracking_events"
        self.delivery_attempts_container = "delivery_attempts"
        
        if not self.endpoint or not self.key:
            raise ValueError("COSMOS_DB_ENDPOINT and COSMOS_DB_KEY environment variables must be set")
        
        self.client = None
        self.database = None
    
    async def __aenter__(self):
        self.client = CosmosClient(self.endpoint, self.key)
        
        # Create database if it doesn't exist
        self.database = await self.client.create_database_if_not_exists(id=self.database_name)
        
        # Create containers if they don't exist
        await self.database.create_container_if_not_exists(
            id=self.parcels_container,
            partition_key=PartitionKey(path="/destination_postcode"),
            offer_throughput=400
        )
        
        await self.database.create_container_if_not_exists(
            id=self.tracking_events_container,
            partition_key=PartitionKey(path="/event_type"),
            offer_throughput=400
        )
        
        await self.database.create_container_if_not_exists(
            id=self.delivery_attempts_container,
            partition_key=PartitionKey(path="/status"),
            offer_throughput=400
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()

# Global instance for the database operations
_db_manager = None

async def get_db_manager():
    """Get or create the database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = CosmosDBManager()
        await _db_manager.__aenter__()
    return _db_manager

# Parcel Management Functions
async def register_parcel(
    barcode: str,
    sender_name: str,
    sender_address: str,
    sender_phone: Optional[str],
    recipient_name: str,
    recipient_address: str,
    recipient_phone: Optional[str],
    destination_postcode: str,
    service_type: str = "standard",
    weight: Optional[float] = None,
    dimensions: Optional[str] = None,
    declared_value: Optional[float] = None,
    special_instructions: Optional[str] = None,
    store_location: str = "unknown"
) -> Dict[str, Any]:
    """Register a new parcel into the logistics network"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    parcel = {
        "id": str(uuid.uuid4()),
        "barcode": barcode,
        "tracking_number": generate_tracking_number(),
        "sender_name": sender_name,
        "sender_address": sender_address,
        "sender_phone": sender_phone,
        "recipient_name": recipient_name,
        "recipient_address": recipient_address,
        "recipient_phone": recipient_phone,
        "destination_postcode": destination_postcode,
        "service_type": service_type,  # standard, express, overnight, registered
        "weight": weight,
        "dimensions": dimensions,
        "declared_value": declared_value,
        "special_instructions": special_instructions,
        "store_location": store_location,
        "registration_timestamp": datetime.now(timezone.utc).isoformat(),
        "current_status": "registered",
        "current_location": store_location,
        "estimated_delivery": calculate_estimated_delivery(service_type),
        "delivery_attempts": 0,
        "is_delivered": False
    }
    
    try:
        created_parcel = await container.create_item(body=parcel)
        print(f"Parcel registered: {barcode} - {tracking_number} for {recipient_name}")
        
        # Create initial tracking event
        await create_tracking_event(
            barcode=barcode,
            event_type="registered",
            location=store_location,
            description=f"Parcel registered at {store_location}",
            scanned_by="store_staff"
        )
        
        return created_parcel
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error registering parcel: {e}")
        raise

async def get_all_parcels() -> List[Dict[str, Any]]:
    """Get all parcels in the system"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        query = "SELECT * FROM c ORDER BY c.registration_timestamp DESC"
        parcels = []
        async for parcel in container.query_items(query=query, enable_cross_partition_query=True):
            parcels.append(parcel)
        return parcels
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting parcels: {e}")
        return []

async def get_parcel_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """Get a specific parcel by barcode"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        query = "SELECT * FROM c WHERE c.barcode = @barcode"
        parameters = [{"name": "@barcode", "value": barcode}]
        
        parcels = []
        async for parcel in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            parcels.append(parcel)
        
        return parcels[0] if parcels else None
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting parcel by barcode: {e}")
        return None

async def get_parcel_by_tracking_number(tracking_number: str) -> Optional[Dict[str, Any]]:
    """Get a specific parcel by tracking number"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        query = "SELECT * FROM c WHERE c.tracking_number = @tracking_number"
        parameters = [{"name": "@tracking_number", "value": tracking_number}]
        
        parcels = []
        async for parcel in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            parcels.append(parcel)
        
        return parcels[0] if parcels else None
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting parcel by tracking number: {e}")
        return None

async def update_parcel_status(barcode: str, status: str, location: str, scanned_by: str = "system") -> bool:
    """Update the status and location of a parcel"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        # First, find the parcel
        parcel = await get_parcel_by_barcode(barcode)
        if not parcel:
            print(f"Parcel with barcode {barcode} not found")
            return False
        
        # Update the parcel
        parcel["current_status"] = status
        parcel["current_location"] = location
        parcel["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        if status == "delivered":
            parcel["is_delivered"] = True
            parcel["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        await container.upsert_item(body=parcel)
        
        # Create tracking event
        await create_tracking_event(
            barcode=barcode,
            event_type=status,
            location=location,
            description=f"Parcel {status} at {location}",
            scanned_by=scanned_by
        )
        
        print(f"Updated parcel {barcode} status to {status} at {location}")
        return True
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error updating parcel status: {e}")
        return False

# Tracking Events Functions
async def create_tracking_event(
    barcode: str,
    event_type: str,
    location: str,
    description: str,
    scanned_by: str = "system",
    additional_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a new tracking event for a parcel"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.tracking_events_container)
    
    event = {
        "id": str(uuid.uuid4()),
        "barcode": barcode,
        "event_type": event_type,  # registered, in_transit, at_facility, out_for_delivery, delivered, exception
        "location": location,
        "description": description,
        "scanned_by": scanned_by,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "additional_info": additional_info or {}
    }
    
    try:
        created_event = await container.create_item(body=event)
        print(f"Tracking event created: {event_type} for {barcode} at {location}")
        return created_event
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error creating tracking event: {e}")
        raise

async def get_parcel_tracking_history(barcode: str) -> List[Dict[str, Any]]:
    """Get all tracking events for a parcel"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.tracking_events_container)
    
    try:
        query = "SELECT * FROM c WHERE c.barcode = @barcode ORDER BY c.timestamp ASC"
        parameters = [{"name": "@barcode", "value": barcode}]
        
        events = []
        async for event in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            events.append(event)
        
        return events
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting tracking history: {e}")
        return []

# Delivery Attempts Functions
async def record_delivery_attempt(
    barcode: str,
    attempt_type: str,  # delivery, redelivery, pickup
    status: str,  # successful, failed, rescheduled
    driver_id: str,
    location: str,
    reason: Optional[str] = None,
    recipient_signature: Optional[str] = None,
    photo_evidence: Optional[str] = None,
    next_attempt_date: Optional[str] = None
) -> Dict[str, Any]:
    """Record a delivery attempt"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    attempt = {
        "id": str(uuid.uuid4()),
        "barcode": barcode,
        "attempt_type": attempt_type,
        "status": status,
        "driver_id": driver_id,
        "location": location,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "recipient_signature": recipient_signature,
        "photo_evidence": photo_evidence,
        "next_attempt_date": next_attempt_date
    }
    
    try:
        created_attempt = await container.create_item(body=attempt)
        
        # Update parcel delivery attempt count
        parcel = await get_parcel_by_barcode(barcode)
        if parcel:
            parcel["delivery_attempts"] = parcel.get("delivery_attempts", 0) + 1
            if status == "successful":
                parcel["is_delivered"] = True
                parcel["delivery_timestamp"] = datetime.now(timezone.utc).isoformat()
                parcel["current_status"] = "delivered"
            
            db_parcel = await get_db_manager()
            container_parcel = db_parcel.database.get_container_client(db_parcel.parcels_container)
            await container_parcel.upsert_item(body=parcel)
        
        # Create tracking event
        await create_tracking_event(
            barcode=barcode,
            event_type="delivery_attempt" if status != "successful" else "delivered",
            location=location,
            description=f"Delivery attempt {status}: {reason or 'No reason provided'}",
            scanned_by=driver_id
        )
        
        print(f"Delivery attempt recorded for {barcode}: {status}")
        return created_attempt
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error recording delivery attempt: {e}")
        raise

async def get_delivery_attempts(barcode: str) -> List[Dict[str, Any]]:
    """Get all delivery attempts for a parcel"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        query = "SELECT * FROM c WHERE c.barcode = @barcode ORDER BY c.timestamp ASC"
        parameters = [{"name": "@barcode", "value": barcode}]
        
        attempts = []
        async for attempt in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            attempts.append(attempt)
        
        return attempts
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting delivery attempts: {e}")
        return []
# Utility Functions
def generate_tracking_number() -> str:
    """Generate a tracking number for parcels"""
    import string
    # Format: 2 letter prefix + 8 digits + 2 letter suffix
    prefixes = ["LP", "EX", "RG", "OV"]  # LastPost, Express, Regular, Overnight
    prefix = random.choice(prefixes)
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    suffix = ''.join([string.ascii_uppercase[random.randint(0, 25)] for _ in range(2)])
    return f"{prefix}{numbers}{suffix}"

def calculate_estimated_delivery(service_type: str) -> str:
    """Calculate estimated delivery date based on service type"""
    from datetime import timedelta
    base_date = datetime.now(timezone.utc)
    
    if service_type == "overnight":
        delivery_date = base_date + timedelta(days=1)
    elif service_type == "express":
        delivery_date = base_date + timedelta(days=2)
    elif service_type == "registered":
        delivery_date = base_date + timedelta(days=3)
    else:  # standard
        delivery_date = base_date + timedelta(days=5)
    
    return delivery_date.isoformat()

# Logistics Workflow Functions
async def get_parcels_by_status(status: str) -> List[Dict[str, Any]]:
    """Get all parcels with a specific status"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        query = "SELECT * FROM c WHERE c.current_status = @status ORDER BY c.registration_timestamp DESC"
        parameters = [{"name": "@status", "value": status}]
        
        parcels = []
        async for parcel in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            parcels.append(parcel)
        
        return parcels
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting parcels by status: {e}")
        return []

async def get_parcels_by_location(location: str) -> List[Dict[str, Any]]:
    """Get all parcels at a specific location"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        query = "SELECT * FROM c WHERE c.current_location = @location ORDER BY c.registration_timestamp DESC"
        parameters = [{"name": "@location", "value": location}]
        
        parcels = []
        async for parcel in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            parcels.append(parcel)
        
        return parcels
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting parcels by location: {e}")
        return []

async def get_driver_deliveries(driver_id: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all parcels assigned to a driver for delivery"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.parcels_container)
    
    try:
        if date:
            query = "SELECT * FROM c WHERE c.current_status = 'out_for_delivery' AND c.assigned_driver = @driver_id"
            parameters = [{"name": "@driver_id", "value": driver_id}]
        else:
            query = "SELECT * FROM c WHERE c.assigned_driver = @driver_id ORDER BY c.registration_timestamp DESC"
            parameters = [{"name": "@driver_id", "value": driver_id}]
        
        parcels = []
        async for parcel in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            parcels.append(parcel)
        
        return parcels
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting driver deliveries: {e}")
        return []

# Request Management Functions (Updated for logistics operations)
async def request_supervisor_approval(
    parcel_barcode: str,
    request_type: str,
    description: str,
    priority: str = "medium",
    requested_by: str = "system"
) -> str:
    """Request supervisor approval for logistics operations"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    request_id = str(uuid.uuid4())
    approval_request = {
        "id": request_id,
        "parcel_barcode": parcel_barcode,
        "request_type": request_type,  # exception_handling, return_to_sender, delivery_redirect, damage_claim
        "description": description,
        "priority": priority,
        "requested_by": requested_by,
        "status": "pending",
        "request_timestamp": datetime.now(timezone.utc).isoformat(),
        "approved_by": None,
        "approval_timestamp": None,
        "comments": None
    }
    
    try:
        await container.create_item(body=approval_request)
        print(f"Supervisor approval requested: {request_id} for parcel {parcel_barcode}")
        return request_id
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error creating supervisor approval request: {e}")
        raise

async def get_approval_status(request_id: str) -> Optional[Dict[str, Any]]:
    """Get the status of a supervisor approval request"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        query = "SELECT * FROM c WHERE c.id = @request_id"
        parameters = [{"name": "@request_id", "value": request_id}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True):
            items.append(item)
        
        return items[0] if items else None
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting approval status: {e}")
        return None

async def get_all_pending_approvals() -> List[Dict[str, Any]]:
    """Get all pending approval requests"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        query = "SELECT * FROM c WHERE c.status = 'pending' AND c.request_type IS NOT NULL ORDER BY c.request_timestamp DESC"
        items = []
        async for item in container.query_items(query=query, enable_cross_partition_query=True):
            items.append(item)
        return items
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting pending approvals: {e}")
        return []

async def get_all_approved_items() -> List[Dict[str, Any]]:
    """Get all approved requests"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        query = "SELECT * FROM c WHERE c.status = 'approved' AND c.request_type IS NOT NULL ORDER BY c.approval_timestamp DESC"
        items = []
        async for item in container.query_items(query=query, enable_cross_partition_query=True):
            items.append(item)
        return items
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error getting approved items: {e}")
        return []

async def approve_request(request_id: str, approved_by: str, comments: Optional[str] = None) -> bool:
    """Approve a pending request"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        # Get the request
        request = await get_approval_status(request_id)
        if not request:
            print(f"Approval request {request_id} not found")
            return False
        
        # Update the request
        request["status"] = "approved"
        request["approved_by"] = approved_by
        request["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
        if comments:
            request["comments"] = comments
        
        await container.upsert_item(body=request)
        print(f"Approved request {request_id} by {approved_by}")
        return True
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error approving request: {e}")
        return False

async def reject_request(request_id: str, rejected_by: str, comments: Optional[str] = None) -> bool:
    """Reject a pending request"""
    db = await get_db_manager()
    container = db.database.get_container_client(db.delivery_attempts_container)
    
    try:
        # Get the request
        request = await get_approval_status(request_id)
        if not request:
            print(f"Approval request {request_id} not found")
            return False
        
        # Update the request
        request["status"] = "rejected"
        request["approved_by"] = rejected_by
        request["approval_timestamp"] = datetime.now(timezone.utc).isoformat()
        if comments:
            request["comments"] = comments
        
        await container.upsert_item(body=request)
        print(f"Rejected request {request_id} by {rejected_by}")
        return True
    except exceptions.CosmosHttpResponseError as e:
        print(f"Error rejecting request: {e}")
        return False

async def add_random_test_parcels(count: int = 5) -> List[Dict[str, Any]]:
    """Add random test parcels for logistics testing"""
    parcels = []
    service_types = ["standard", "express", "overnight", "registered"]
    # Australian postcodes for major cities
    postcodes = ["2000", "3000", "4000", "5000", "6000", "7000", "0200", "3141", "2007", "4006"]
    # Australian store locations
    store_locations = ["Store_Sydney_CBD", "Store_Melbourne_CBD", "Store_Brisbane_CBD", "Store_Adelaide_CBD", "Store_Perth_CBD"]
    
    for _ in range(count):
        barcode = f"LP{random.randint(100000, 999999)}"
        service_type = random.choice(service_types)
        postcode = random.choice(postcodes)
        store = random.choice(store_locations)
        
        parcel = await register_parcel(
            barcode=barcode,
            sender_name=fake.name(),
            sender_address=fake.address(),
            sender_phone=fake.phone_number() if random.choice([True, False]) else None,
            recipient_name=fake.name(),
            recipient_address=fake.address(),
            recipient_phone=fake.phone_number() if random.choice([True, False]) else None,
            destination_postcode=postcode,
            service_type=service_type,
            weight=round(random.uniform(0.1, 25.0), 2),
            dimensions=f"{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 30)}cm",
            declared_value=round(random.uniform(10.0, 500.0), 2) if random.choice([True, False]) else None,
            special_instructions=fake.sentence() if random.choice([True, False]) else None,
            store_location=store
        )
        parcels.append(parcel)
    
    return parcels

async def add_random_approval_requests(count: int = 3) -> List[str]:
    """Add random approval requests for logistics operations"""
    request_ids = []
    request_types = ["exception_handling", "return_to_sender", "delivery_redirect", "damage_claim", "lost_package"]
    priorities = ["low", "medium", "high", "critical"]
    
    # Get some existing parcels
    parcels = await get_all_parcels()
    if not parcels:
        # Add some parcels first
        await add_random_test_parcels(5)
        parcels = await get_all_parcels()
    
    for _ in range(count):
        if parcels:
            parcel = random.choice(parcels)
            request_type = random.choice(request_types)
            
            request_id = await request_supervisor_approval(
                parcel_barcode=parcel["barcode"],
                request_type=request_type,
                description=f"Request for {request_type} on parcel to {parcel['recipient_name']}",
                priority=random.choice(priorities),
                requested_by="logistics_agent"
            )
            request_ids.append(request_id)
    
    return request_ids

# Wrapper functions for backward compatibility with existing agent tools
def get_all_scanned_items_sync() -> List[Dict[str, Any]]:
    """Synchronous wrapper for get_all_parcels (backward compatibility)"""
    return asyncio.run(get_all_parcels())

def add_scanned_item_sync(barcode: str, item_name: str, sender_name: str, recipient_name: str, recipient_address: str) -> Dict[str, Any]:
    """Synchronous wrapper for register_parcel (backward compatibility)"""
    # Extract postcode from address (simple extraction)
    address_parts = recipient_address.split(',')
    postcode = address_parts[-1].strip() if address_parts else "UNKNOWN"
    
    return asyncio.run(register_parcel(
        barcode=barcode,
        sender_name=sender_name,
        sender_address=f"Store Location - {sender_name}",
        sender_phone=None,
        recipient_name=recipient_name,
        recipient_address=recipient_address,
        recipient_phone=None,
        destination_postcode=postcode,
        service_type="standard",
        store_location="Store_Central"
    ))

def request_human_approval_sync(item_barcode: str, request_type: str, description: str) -> str:
    """Synchronous wrapper for request_supervisor_approval"""
    return asyncio.run(request_supervisor_approval(item_barcode, request_type, description))

def get_human_approval_status_sync(request_id: str) -> Optional[Dict[str, Any]]:
    """Synchronous wrapper for get_approval_status"""
    return asyncio.run(get_approval_status(request_id))

def get_all_pending_approvals_sync() -> List[Dict[str, Any]]:
    """Synchronous wrapper for get_all_pending_approvals"""
    return asyncio.run(get_all_pending_approvals())

def get_all_approved_items_sync() -> List[Dict[str, Any]]:
    """Synchronous wrapper for get_all_approved_items"""
    return asyncio.run(get_all_approved_items())

def approve_request_sync(request_id: str, approved_by: str, comments: Optional[str] = None) -> bool:
    """Synchronous wrapper for approve_request"""
    return asyncio.run(approve_request(request_id, approved_by, comments))

def reject_request_sync(request_id: str, rejected_by: str, comments: Optional[str] = None) -> bool:
    """Synchronous wrapper for reject_request"""
    return asyncio.run(reject_request(request_id, rejected_by, comments))

def add_random_approval_items_sync(count: int = 3) -> List[str]:
    """Synchronous wrapper for add_random_approval_requests"""
    return asyncio.run(add_random_approval_requests(count))

# Cleanup function
async def cleanup_database():
    """Delete all items from both containers (for testing purposes)"""
    global _db_manager
    if _db_manager:
        await _db_manager.__aexit__(None, None, None)
        _db_manager = None