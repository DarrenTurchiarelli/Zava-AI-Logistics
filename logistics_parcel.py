"""
Zava - Parcel Management Module
Handles parcel registration, tracking, and status management
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Parcel:
    """Represents a parcel in the Zava system"""

    tracking_number: str
    sender_name: str
    sender_address: str
    sender_phone: str
    recipient_name: str
    recipient_address: str
    recipient_phone: str
    postcode: str
    state: str
    weight_kg: float
    package_type: str
    special_instructions: Optional[str]
    status: str
    store_id: Optional[str] = None
    driver_id: Optional[str] = None
    pickup_timestamp: Optional[datetime] = None
    delivery_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None


def get_state_from_postcode(postcode: str) -> str:
    """
    Determine Australian state from postcode using accurate range mapping

    Zava Postcode Ranges:
    - NSW: 1000-2599, 2619-2899, 2921-2999
    - ACT: 200-299, 2600-2618, 2900-2920
    - VIC: 3000-3999, 8000-8999
    - QLD: 4000-4999, 9000-9999
    - SA: 5000-5999
    - WA: 6000-6797, 6800-6999
    - TAS: 7000-7999
    - NT: 800-899
    """
    try:
        pc = int(postcode)

        # NSW ranges
        if (1000 <= pc <= 2599) or (2619 <= pc <= 2899) or (2921 <= pc <= 2999):
            return "NSW"

        # ACT ranges
        if (200 <= pc <= 299) or (2600 <= pc <= 2618) or (2900 <= pc <= 2920):
            return "ACT"

        # VIC ranges (including 3004 for Carlton)
        if (3000 <= pc <= 3999) or (8000 <= pc <= 8999):
            return "VIC"

        # QLD ranges
        if (4000 <= pc <= 4999) or (9000 <= pc <= 9999):
            return "QLD"

        # SA range
        if 5000 <= pc <= 5999:
            return "SA"

        # WA ranges
        if (6000 <= pc <= 6797) or (6800 <= pc <= 6999):
            return "WA"

        # TAS range
        if 7000 <= pc <= 7999:
            return "TAS"

        # NT range
        if 800 <= pc <= 899:
            return "NT"

        return "UNKNOWN"

    except ValueError:
        return "INVALID"


def generate_tracking_number(state: str) -> str:
    """Generate a unique tracking number with state prefix"""
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"DT{state}{unique_id}"


def create_parcel(
    sender_name: str,
    sender_address: str,
    sender_phone: str,
    recipient_name: str,
    recipient_address: str,
    recipient_phone: str,
    postcode: str,
    weight_kg: float,
    package_type: str = "Standard",
    special_instructions: Optional[str] = None,
) -> Parcel:
    """
    Create a new parcel with automatic state detection and tracking number generation

    Args:
        sender_name: Name of the sender
        sender_address: Full sender address
        sender_phone: Sender contact phone
        recipient_name: Name of the recipient
        recipient_address: Full recipient address
        recipient_phone: Recipient contact phone
        postcode: Australian postcode (determines state)
        weight_kg: Package weight in kilograms
        package_type: Type of package (Standard, Express, Fragile, etc.)
        special_instructions: Optional delivery instructions

    Returns:
        Parcel object with generated tracking number and status
    """
    state = get_state_from_postcode(postcode)
    tracking_number = generate_tracking_number(state)

    return Parcel(
        tracking_number=tracking_number,
        sender_name=sender_name,
        sender_address=sender_address,
        sender_phone=sender_phone,
        recipient_name=recipient_name,
        recipient_address=recipient_address,
        recipient_phone=recipient_phone,
        postcode=postcode,
        state=state,
        weight_kg=weight_kg,
        package_type=package_type,
        special_instructions=special_instructions,
        status="Registered",
        created_at=datetime.now(),
    )


def validate_parcel_data(parcel: Parcel) -> tuple[bool, list[str]]:
    """
    Validate parcel data for completeness and accuracy

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate required fields
    if not parcel.sender_name or len(parcel.sender_name.strip()) < 2:
        errors.append("Sender name is required and must be at least 2 characters")

    if not parcel.recipient_name or len(parcel.recipient_name.strip()) < 2:
        errors.append("Recipient name is required and must be at least 2 characters")

    if not parcel.sender_address or len(parcel.sender_address.strip()) < 5:
        errors.append("Sender address is required and must be at least 5 characters")

    if not parcel.recipient_address or len(parcel.recipient_address.strip()) < 5:
        errors.append("Recipient address is required and must be at least 5 characters")

    # Validate phone numbers (basic Australian format)
    if not parcel.sender_phone or len(parcel.sender_phone.replace(" ", "").replace("-", "")) < 10:
        errors.append("Valid sender phone number is required (minimum 10 digits)")

    if not parcel.recipient_phone or len(parcel.recipient_phone.replace(" ", "").replace("-", "")) < 10:
        errors.append("Valid recipient phone number is required (minimum 10 digits)")

    # Validate postcode
    if parcel.state == "UNKNOWN":
        errors.append(f"Postcode {parcel.postcode} does not map to a valid Australian state")
    elif parcel.state == "INVALID":
        errors.append(f"Postcode {parcel.postcode} is not a valid number")

    # Validate weight
    if parcel.weight_kg <= 0:
        errors.append("Weight must be greater than 0 kg")
    elif parcel.weight_kg > 30:
        errors.append("Weight exceeds maximum limit of 30 kg (contact freight department)")

    return (len(errors) == 0, errors)


def update_parcel_status(parcel: Parcel, new_status: str, driver_id: Optional[str] = None) -> Parcel:
    """
    Update parcel status with automatic timestamp management

    Valid status transitions:
    - Registered → In Transit
    - In Transit → Out for Delivery
    - Out for Delivery → Delivered
    - Any → Failed Delivery (with reason)
    """
    valid_statuses = [
        "Registered",
        "In Transit",
        "At Sorting Facility",
        "Out for Delivery",
        "Delivered",
        "Failed Delivery",
        "Returned to Sender",
    ]

    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

    parcel.status = new_status

    # Automatic timestamp management
    if new_status == "Out for Delivery" and driver_id:
        parcel.driver_id = driver_id
        parcel.pickup_timestamp = datetime.now()

    if new_status == "Delivered":
        parcel.delivery_timestamp = datetime.now()

    return parcel


def get_parcel_info(parcel: Parcel) -> str:
    """Get formatted parcel information for display"""
    info = f"""
Zava Parcel Information
================================
Tracking Number: {parcel.tracking_number}
Status: {parcel.status}
State: {parcel.state} (Postcode: {parcel.postcode})

Sender Details:
  Name: {parcel.sender_name}
  Address: {parcel.sender_address}
  Phone: {parcel.sender_phone}

Recipient Details:
  Name: {parcel.recipient_name}
  Address: {parcel.recipient_address}
  Phone: {parcel.recipient_phone}

Package Details:
  Type: {parcel.package_type}
  Weight: {parcel.weight_kg} kg
  Special Instructions: {parcel.special_instructions or 'None'}

Tracking:
  Created: {parcel.created_at.strftime('%Y-%m-%d %H:%M:%S') if parcel.created_at else 'N/A'}
  Driver: {parcel.driver_id or 'Not assigned'}
  Pickup: {parcel.pickup_timestamp.strftime('%Y-%m-%d %H:%M:%S') if parcel.pickup_timestamp else 'Not picked up'}
  Delivery: {parcel.delivery_timestamp.strftime('%Y-%m-%d %H:%M:%S') if parcel.delivery_timestamp else 'Not delivered'}
"""
    return info


# Example usage and testing
if __name__ == "__main__":
    print("Zava - Parcel Management Module")
    print("=" * 50)

    # Test postcode mapping
    test_postcodes = ["3004", "2000", "4000", "5000", "6000", "7000", "800", "2600"]
    print("\nPostcode to State Mapping:")
    for pc in test_postcodes:
        state = get_state_from_postcode(pc)
        print(f"  {pc} → {state}")

    # Create sample parcel
    print("\nCreating sample parcel...")
    parcel = create_parcel(
        sender_name="Zava Warehouse",
        sender_address="123 Distribution Drive, Melbourne VIC",
        sender_phone="03-9876-5432",
        recipient_name="John Smith",
        recipient_address="456 Customer Street, Carlton VIC 3004",
        recipient_phone="0412-345-678",
        postcode="3004",
        weight_kg=2.5,
        package_type="Express",
        special_instructions="Leave at front door if not home",
    )

    # Validate parcel
    is_valid, errors = validate_parcel_data(parcel)
    if is_valid:
        print("✓ Parcel validation passed")
        print(get_parcel_info(parcel))
    else:
        print("✗ Parcel validation failed:")
        for error in errors:
            print(f"  - {error}")
