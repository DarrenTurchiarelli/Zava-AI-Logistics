"""
Zava - Driver Management Module
Manages driver profiles, vehicle assignments, and delivery routes
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Driver:
    """Represents a Zava delivery driver"""

    driver_id: str
    name: str
    phone: str
    email: str
    license_number: str
    vehicle_registration: str
    vehicle_type: str
    max_capacity_kg: float
    current_load_kg: float
    assigned_state: str
    status: str  # Available, On Route, Off Duty
    assigned_parcels: List[str]  # List of tracking numbers
    store_id: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None


def create_driver(
    driver_id: str,
    name: str,
    phone: str,
    email: str,
    license_number: str,
    vehicle_registration: str,
    vehicle_type: str = "Van",
    max_capacity_kg: float = 500.0,
    assigned_state: str = "VIC",
) -> Driver:
    """
    Register a new driver in the Zava system

    Args:
        driver_id: Unique driver identifier (e.g., DRV001)
        name: Full name of the driver
        phone: Contact phone number
        email: Email address
        license_number: Driver's license number
        vehicle_registration: Vehicle registration plate
        vehicle_type: Type of delivery vehicle (Van, Truck, Bike, etc.)
        max_capacity_kg: Maximum cargo weight capacity
        assigned_state: Primary operating state

    Returns:
        Driver object initialized with available status
    """
    return Driver(
        driver_id=driver_id,
        name=name,
        phone=phone,
        email=email,
        license_number=license_number,
        vehicle_registration=vehicle_registration,
        vehicle_type=vehicle_type,
        max_capacity_kg=max_capacity_kg,
        current_load_kg=0.0,
        assigned_state=assigned_state,
        status="Available",
        assigned_parcels=[],
        store_id=None,
    )


def assign_parcel_to_driver(driver: Driver, tracking_number: str, weight_kg: float) -> tuple[bool, str]:
    """
    Assign a parcel to a driver's delivery route

    Returns:
        Tuple of (success, message)
    """
    # Check if driver is available
    if driver.status == "Off Duty":
        return False, f"Driver {driver.driver_id} is off duty"

    # Check capacity
    if driver.current_load_kg + weight_kg > driver.max_capacity_kg:
        return (
            False,
            f"Exceeds driver capacity: {driver.current_load_kg + weight_kg:.1f} kg > {driver.max_capacity_kg:.1f} kg",
        )

    # Assign parcel
    if tracking_number not in driver.assigned_parcels:
        driver.assigned_parcels.append(tracking_number)
        driver.current_load_kg += weight_kg
        driver.status = "On Route"
        return True, f"Parcel {tracking_number} assigned to driver {driver.driver_id}"
    else:
        return False, f"Parcel {tracking_number} already assigned to this driver"


def remove_parcel_from_driver(driver: Driver, tracking_number: str, weight_kg: float) -> tuple[bool, str]:
    """
    Remove a parcel from driver's delivery route (after delivery or reassignment)

    Returns:
        Tuple of (success, message)
    """
    if tracking_number in driver.assigned_parcels:
        driver.assigned_parcels.remove(tracking_number)
        driver.current_load_kg -= weight_kg

        # Update status if no more parcels
        if len(driver.assigned_parcels) == 0:
            driver.status = "Available"
            driver.current_load_kg = 0.0  # Reset to ensure no floating point errors

        return True, f"Parcel {tracking_number} removed from driver {driver.driver_id}"
    else:
        return False, f"Parcel {tracking_number} not found in driver {driver.driver_id}'s route"


def start_driver_shift(driver: Driver, store_id: str) -> Driver:
    """Start a driver's shift at a specific store"""
    driver.status = "Available"
    driver.store_id = store_id
    driver.shift_start = datetime.now()
    driver.shift_end = None
    driver.assigned_parcels = []
    driver.current_load_kg = 0.0
    return driver


def end_driver_shift(driver: Driver) -> tuple[bool, str]:
    """
    End a driver's shift

    Returns:
        Tuple of (success, message)
    """
    if len(driver.assigned_parcels) > 0:
        return False, f"Cannot end shift: {len(driver.assigned_parcels)} parcels still assigned"

    driver.status = "Off Duty"
    driver.shift_end = datetime.now()
    driver.store_id = None
    return True, f"Shift ended for driver {driver.driver_id}"


def get_driver_capacity_status(driver: Driver) -> str:
    """Get driver's current capacity utilization"""
    utilization_pct = (driver.current_load_kg / driver.max_capacity_kg) * 100

    if utilization_pct < 50:
        status_msg = "Low utilization - can accept more parcels"
    elif utilization_pct < 80:
        status_msg = "Good utilization - operating efficiently"
    elif utilization_pct < 100:
        status_msg = "High utilization - near capacity"
    else:
        status_msg = "At capacity - cannot accept more parcels"

    return f"{driver.driver_id}: {driver.current_load_kg:.1f}/{driver.max_capacity_kg:.1f} kg ({utilization_pct:.1f}%) - {status_msg}"


def get_driver_info(driver: Driver) -> str:
    """Get formatted driver information for display"""
    info = f"""
Zava Driver Information
================================
Driver ID: {driver.driver_id}
Name: {driver.name}
Status: {driver.status}

Contact:
  Phone: {driver.phone}
  Email: {driver.email}

License & Vehicle:
  License: {driver.license_number}
  Vehicle: {driver.vehicle_type} ({driver.vehicle_registration})
  Assigned State: {driver.assigned_state}

Capacity:
  Current Load: {driver.current_load_kg:.1f} kg / {driver.max_capacity_kg:.1f} kg
  Utilization: {(driver.current_load_kg / driver.max_capacity_kg * 100):.1f}%
  Assigned Parcels: {len(driver.assigned_parcels)}

Shift:
  Store: {driver.store_id or 'Not on shift'}
  Start: {driver.shift_start.strftime('%Y-%m-%d %H:%M:%S') if driver.shift_start else 'N/A'}
  End: {driver.shift_end.strftime('%Y-%m-%d %H:%M:%S') if driver.shift_end else 'In progress' if driver.shift_start else 'N/A'}

Current Route:
"""

    if driver.assigned_parcels:
        for i, tracking_num in enumerate(driver.assigned_parcels, 1):
            info += f"  {i}. {tracking_num}\n"
    else:
        info += "  No parcels assigned\n"

    return info


def validate_driver_data(driver: Driver) -> tuple[bool, list[str]]:
    """
    Validate driver data for completeness and accuracy

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate required fields
    if not driver.name or len(driver.name.strip()) < 2:
        errors.append("Driver name is required and must be at least 2 characters")

    if not driver.phone or len(driver.phone.replace(" ", "").replace("-", "")) < 10:
        errors.append("Valid phone number is required (minimum 10 digits)")

    if not driver.email or "@" not in driver.email:
        errors.append("Valid email address is required")

    if not driver.license_number or len(driver.license_number) < 5:
        errors.append("Valid driver's license number is required")

    if not driver.vehicle_registration or len(driver.vehicle_registration) < 4:
        errors.append("Valid vehicle registration is required")

    # Validate capacity
    if driver.max_capacity_kg <= 0:
        errors.append("Maximum capacity must be greater than 0 kg")

    if driver.current_load_kg < 0:
        errors.append("Current load cannot be negative")

    if driver.current_load_kg > driver.max_capacity_kg:
        errors.append(
            f"Current load ({driver.current_load_kg} kg) exceeds maximum capacity ({driver.max_capacity_kg} kg)"
        )

    # Validate status
    valid_statuses = ["Available", "On Route", "Off Duty"]
    if driver.status not in valid_statuses:
        errors.append(f"Invalid status: {driver.status}. Must be one of {valid_statuses}")

    return (len(errors) == 0, errors)


# Example usage and testing
if __name__ == "__main__":
    print("Zava - Driver Management Module")
    print("=" * 50)

    # Create sample driver
    print("\nCreating sample driver...")
    driver = create_driver(
        driver_id="DRV001",
        name="Sarah Johnson",
        phone="0412-345-678",
        email="sarah.johnson@dtlogistics.com.au",
        license_number="VIC123456",
        vehicle_registration="ABC123",
        vehicle_type="Van",
        max_capacity_kg=500.0,
        assigned_state="VIC",
    )

    # Validate driver
    is_valid, errors = validate_driver_data(driver)
    if is_valid:
        print("✓ Driver validation passed")
    else:
        print("✗ Driver validation failed:")
        for error in errors:
            print(f"  - {error}")

    # Start shift
    print("\nStarting driver shift...")
    start_driver_shift(driver, "STORE_VIC_001")

    # Assign parcels
    print("\nAssigning parcels...")
    success, msg = assign_parcel_to_driver(driver, "DTVIC12345678", 2.5)
    print(f"  {msg}")

    success, msg = assign_parcel_to_driver(driver, "DTVIC87654321", 5.2)
    print(f"  {msg}")

    success, msg = assign_parcel_to_driver(driver, "DTVICABCDEF12", 3.8)
    print(f"  {msg}")

    # Check capacity
    print(f"\n{get_driver_capacity_status(driver)}")

    # Display driver info
    print(get_driver_info(driver))

    # Simulate delivery
    print("\nSimulating parcel delivery...")
    success, msg = remove_parcel_from_driver(driver, "DTVIC12345678", 2.5)
    print(f"  {msg}")

    print(f"\n{get_driver_capacity_status(driver)}")


# --- Menu Integration Functions ---


async def verify_courier_identity():
    """Verify courier identity with Zava credentials"""
    print("\n" + "=" * 70)
    print("🪪 VERIFY COURIER IDENTITY")
    print("=" * 70)

    driver_id = input("\n👤 Enter Driver ID (e.g., DRV001): ").strip().upper()

    # Simulate verification process
    print("\n🔍 Verifying credentials...")
    await asyncio.sleep(1)

    # Mock verification data
    valid_drivers = {
        "DRV001": {"name": "Sarah Johnson", "license": "VIC-234567", "vehicle": "ABC-123"},
        "DRV002": {"name": "Michael Chen", "license": "VIC-345678", "vehicle": "DEF-456"},
        "DRV003": {"name": "Emma Wilson", "license": "VIC-456789", "vehicle": "GHI-789"},
    }

    if driver_id in valid_drivers:
        driver = valid_drivers[driver_id]
        print("\n✅ VERIFICATION SUCCESSFUL")
        print(f"  Driver: {driver['name']}")
        print(f"  License: {driver['license']}")
        print(f"  Vehicle: {driver['vehicle']}")
        print(f"  Status: Active")
        print(f"  Verified: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("\n❌ VERIFICATION FAILED")
        print("  Driver ID not found in system")
        print("  Please contact Zava dispatch")


async def complete_proof_of_delivery():
    """Complete proof of delivery for a parcel"""
    print("\n" + "=" * 70)
    print("📸 PROOF OF DELIVERY")
    print("=" * 70)

    tracking_number = input("\n📦 Enter Tracking Number: ").strip().upper()

    print("\n📋 Delivery Confirmation Options:")
    print("  1. Signature capture")
    print("  2. Photo evidence")
    print("  3. GPS location")
    print("  4. Contactless delivery (safe place)")

    method = input("\n👉 Select method (1-4): ").strip()

    method_names = {"1": "Signature Capture", "2": "Photo Evidence", "3": "GPS Location", "4": "Contactless Delivery"}

    if method in method_names:
        print(f"\n📸 Recording {method_names[method]}...")
        await asyncio.sleep(1)

        print("\n✅ DELIVERY COMPLETED")
        print(f"  Tracking: {tracking_number}")
        print(f"  Method: {method_names[method]}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Location: {'GPS coordinates recorded' if method == '3' else 'Address confirmed'}")

        # Ask for notes
        notes = input("\n📝 Delivery notes (optional): ").strip()
        if notes:
            print(f"  Notes: {notes}")
    else:
        print("❌ Invalid selection")


async def offline_mode_operations():
    """Handle operations when network connectivity is unavailable"""
    print("\n" + "=" * 70)
    print("📴 OFFLINE MODE OPERATIONS")
    print("=" * 70)

    print("\n📱 Offline Capabilities:")
    print("  ✅ View cached delivery manifest")
    print("  ✅ Record proof of delivery locally")
    print("  ✅ Update delivery status (queued)")
    print("  ✅ Access driver assignment details")
    print("  ⏳ Sync when connection restored")

    print("\n🔄 Current Status:")
    print("  Network: Offline")
    print("  Cached Deliveries: 12")
    print("  Pending Sync: 3 deliveries")
    print("  Last Sync: 2 hours ago")

    action = input("\n👉 Action [view/record/sync/exit]: ").strip().lower()

    if action == "view":
        print("\n📦 Cached Delivery Manifest:")
        for i in range(1, 6):
            print(
                f"  {i}. DTVIC{random.randint(10000000, 99999999)} - {random.choice(['Melbourne CBD', 'Carlton', 'Richmond', 'St Kilda'])}"
            )

    elif action == "record":
        tracking = input("📦 Tracking Number: ").strip()
        print(f"\n✅ Delivery recorded locally for {tracking}")
        print("  Will sync when connection restored")

    elif action == "sync":
        print("\n🔄 Attempting to sync...")
        await asyncio.sleep(2)
        print("❌ Network still unavailable")
        print("  Will retry automatically")

    elif action == "exit":
        print("👋 Exiting offline mode")
    else:
        print("❌ Invalid action")
