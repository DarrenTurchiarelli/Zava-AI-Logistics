"""
DT Logistics - Store Management Module
Manages distribution centers, sorting facilities, and store operations
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Store:
    """Represents a DT Logistics distribution center or store"""
    store_id: str
    store_name: str
    address: str
    city: str
    state: str
    postcode: str
    phone: str
    email: str
    store_type: str  # Distribution Center, Sorting Facility, Retail Store
    capacity: int
    current_inventory: int
    operating_states: List[str]
    manager_name: str
    operating_hours: str
    parcels_in_store: List[str] = field(default_factory=list)
    drivers_assigned: List[str] = field(default_factory=list)
    statistics: Dict[str, int] = field(default_factory=dict)

def create_store(
    store_id: str,
    store_name: str,
    address: str,
    city: str,
    state: str,
    postcode: str,
    phone: str,
    email: str,
    store_type: str = "Distribution Center",
    capacity: int = 10000,
    operating_states: Optional[List[str]] = None,
    manager_name: str = "Store Manager",
    operating_hours: str = "Mon-Fri 6:00-18:00"
) -> Store:
    """
    Create a new DT Logistics store or distribution center
    
    Args:
        store_id: Unique store identifier (e.g., STORE_VIC_001)
        store_name: Display name of the store
        address: Street address
        city: City location
        state: Australian state
        postcode: Postal code
        phone: Contact phone
        email: Contact email
        store_type: Type of facility
        capacity: Maximum parcel capacity
        operating_states: List of states this store services
        manager_name: Store manager's name
        operating_hours: Operating hours description
    
    Returns:
        Store object with initialized statistics
    """
    if operating_states is None:
        operating_states = [state]
    
    return Store(
        store_id=store_id,
        store_name=store_name,
        address=address,
        city=city,
        state=state,
        postcode=postcode,
        phone=phone,
        email=email,
        store_type=store_type,
        capacity=capacity,
        current_inventory=0,
        operating_states=operating_states,
        manager_name=manager_name,
        operating_hours=operating_hours,
        parcels_in_store=[],
        drivers_assigned=[],
        statistics={
            "total_processed": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "total_returned": 0
        }
    )

def add_parcel_to_store(store: Store, tracking_number: str) -> tuple[bool, str]:
    """
    Add a parcel to store inventory
    
    Returns:
        Tuple of (success, message)
    """
    # Check capacity
    if store.current_inventory >= store.capacity:
        return False, f"Store {store.store_id} at capacity ({store.capacity} parcels)"
    
    # Check for duplicates
    if tracking_number in store.parcels_in_store:
        return False, f"Parcel {tracking_number} already in store {store.store_id}"
    
    # Add parcel
    store.parcels_in_store.append(tracking_number)
    store.current_inventory += 1
    store.statistics["total_processed"] += 1
    
    return True, f"Parcel {tracking_number} added to store {store.store_id}"

def remove_parcel_from_store(store: Store, tracking_number: str, reason: str = "dispatched") -> tuple[bool, str]:
    """
    Remove a parcel from store inventory
    
    Args:
        store: Store object
        tracking_number: Parcel tracking number
        reason: Reason for removal (dispatched, delivered, failed, returned)
    
    Returns:
        Tuple of (success, message)
    """
    if tracking_number not in store.parcels_in_store:
        return False, f"Parcel {tracking_number} not found in store {store.store_id}"
    
    # Remove parcel
    store.parcels_in_store.remove(tracking_number)
    store.current_inventory -= 1
    
    # Update statistics
    if reason == "delivered":
        store.statistics["total_delivered"] += 1
    elif reason == "failed":
        store.statistics["total_failed"] += 1
    elif reason == "returned":
        store.statistics["total_returned"] += 1
    
    return True, f"Parcel {tracking_number} removed from store {store.store_id} ({reason})"

def assign_driver_to_store(store: Store, driver_id: str) -> tuple[bool, str]:
    """
    Assign a driver to a store for shift operations
    
    Returns:
        Tuple of (success, message)
    """
    if driver_id in store.drivers_assigned:
        return False, f"Driver {driver_id} already assigned to store {store.store_id}"
    
    store.drivers_assigned.append(driver_id)
    return True, f"Driver {driver_id} assigned to store {store.store_id}"

def remove_driver_from_store(store: Store, driver_id: str) -> tuple[bool, str]:
    """
    Remove a driver from store assignments (end of shift)
    
    Returns:
        Tuple of (success, message)
    """
    if driver_id not in store.drivers_assigned:
        return False, f"Driver {driver_id} not assigned to store {store.store_id}"
    
    store.drivers_assigned.remove(driver_id)
    return True, f"Driver {driver_id} removed from store {store.store_id}"

def get_store_capacity_status(store: Store) -> str:
    """Get store's current capacity utilization"""
    utilization_pct = (store.current_inventory / store.capacity) * 100
    
    if utilization_pct < 50:
        status_msg = "Low utilization - accepting parcels"
    elif utilization_pct < 80:
        status_msg = "Normal operations"
    elif utilization_pct < 95:
        status_msg = "High utilization - near capacity"
    else:
        status_msg = "Critical - at capacity limit"
    
    return f"{store.store_id}: {store.current_inventory}/{store.capacity} parcels ({utilization_pct:.1f}%) - {status_msg}"

def get_store_performance_summary(store: Store) -> str:
    """Get store performance metrics"""
    total = store.statistics["total_processed"]
    delivered = store.statistics["total_delivered"]
    failed = store.statistics["total_failed"]
    returned = store.statistics["total_returned"]
    
    success_rate = (delivered / total * 100) if total > 0 else 0
    failure_rate = (failed / total * 100) if total > 0 else 0
    
    return f"""
Store Performance: {store.store_id}
Total Processed: {total:,}
Delivered: {delivered:,} ({success_rate:.1f}%)
Failed: {failed:,} ({failure_rate:.1f}%)
Returned: {returned:,}
"""

def get_store_info(store: Store) -> str:
    """Get formatted store information for display"""
    info = f"""
DT Logistics Store Information
================================
Store ID: {store.store_id}
Name: {store.store_name}
Type: {store.store_type}

Location:
  Address: {store.address}
  City: {store.city}, {store.state} {store.postcode}
  Phone: {store.phone}
  Email: {store.email}

Operations:
  Manager: {store.manager_name}
  Hours: {store.operating_hours}
  Services States: {', '.join(store.operating_states)}

Capacity:
  Current Inventory: {store.current_inventory:,} / {store.capacity:,} parcels
  Utilization: {(store.current_inventory / store.capacity * 100):.1f}%
  Parcels in Store: {len(store.parcels_in_store)}
  Assigned Drivers: {len(store.drivers_assigned)}

Performance Statistics:
  Total Processed: {store.statistics['total_processed']:,}
  Total Delivered: {store.statistics['total_delivered']:,}
  Total Failed: {store.statistics['total_failed']:,}
  Total Returned: {store.statistics['total_returned']:,}
  Success Rate: {(store.statistics['total_delivered'] / store.statistics['total_processed'] * 100) if store.statistics['total_processed'] > 0 else 0:.1f}%
"""
    return info

def validate_store_data(store: Store) -> tuple[bool, list[str]]:
    """
    Validate store data for completeness and accuracy
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Validate required fields
    if not store.store_name or len(store.store_name.strip()) < 2:
        errors.append("Store name is required and must be at least 2 characters")
    
    if not store.address or len(store.address.strip()) < 5:
        errors.append("Store address is required and must be at least 5 characters")
    
    if not store.phone or len(store.phone.replace(" ", "").replace("-", "")) < 10:
        errors.append("Valid phone number is required (minimum 10 digits)")
    
    if not store.email or "@" not in store.email:
        errors.append("Valid email address is required")
    
    # Validate capacity
    if store.capacity <= 0:
        errors.append("Store capacity must be greater than 0")
    
    if store.current_inventory < 0:
        errors.append("Current inventory cannot be negative")
    
    if store.current_inventory > store.capacity:
        errors.append(f"Current inventory ({store.current_inventory}) exceeds capacity ({store.capacity})")
    
    # Validate store type
    valid_types = ["Distribution Center", "Sorting Facility", "Retail Store", "Pickup Point"]
    if store.store_type not in valid_types:
        errors.append(f"Invalid store type: {store.store_type}. Must be one of {valid_types}")
    
    # Validate operating states
    valid_states = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]
    for state in store.operating_states:
        if state not in valid_states:
            errors.append(f"Invalid operating state: {state}")
    
    return (len(errors) == 0, errors)

# Example usage and testing
if __name__ == "__main__":
    print("DT Logistics - Store Management Module")
    print("=" * 50)
    
    # Create sample store
    print("\nCreating sample distribution center...")
    store = create_store(
        store_id="STORE_VIC_001",
        store_name="DT Logistics Melbourne Distribution Center",
        address="123 Distribution Drive",
        city="Melbourne",
        state="VIC",
        postcode="3000",
        phone="03-9876-5432",
        email="melbourne.dc@dtlogistics.com.au",
        store_type="Distribution Center",
        capacity=10000,
        operating_states=["VIC", "TAS", "SA"],
        manager_name="Michael Chen",
        operating_hours="Mon-Sun 24/7"
    )
    
    # Validate store
    is_valid, errors = validate_store_data(store)
    if is_valid:
        print("✓ Store validation passed")
    else:
        print("✗ Store validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    # Add parcels
    print("\nAdding parcels to store...")
    for i in range(5):
        tracking = f"DTVIC{str(i).zfill(8)}"
        success, msg = add_parcel_to_store(store, tracking)
        print(f"  {msg}")
    
    # Assign drivers
    print("\nAssigning drivers...")
    success, msg = assign_driver_to_store(store, "DRV001")
    print(f"  {msg}")
    success, msg = assign_driver_to_store(store, "DRV002")
    print(f"  {msg}")
    
    # Check capacity
    print(f"\n{get_store_capacity_status(store)}")
    
    # Display store info
    print(get_store_info(store))
