"""
DT Logistics - Delivery Management Module
Manages delivery execution, proof of delivery, and delivery status updates
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import uuid

@dataclass
class Delivery:
    """Represents a delivery attempt"""
    delivery_id: str
    tracking_number: str
    driver_id: str
    attempt_number: int
    delivery_date: datetime
    delivery_status: str  # Successful, Failed, Pending
    recipient_name: Optional[str] = None
    signature: Optional[str] = None
    photo_proof: Optional[str] = None
    delivery_notes: Optional[str] = None
    failed_reason: Optional[str] = None
    gps_coordinates: Optional[tuple[float, float]] = None

def create_delivery_attempt(
    tracking_number: str,
    driver_id: str,
    attempt_number: int = 1
) -> Delivery:
    """
    Create a new delivery attempt record
    
    Args:
        tracking_number: Parcel tracking number
        driver_id: Driver making the delivery
        attempt_number: Delivery attempt count (1 for first attempt)
    
    Returns:
        Delivery object
    """
    delivery_id = f"DEL_{uuid.uuid4().hex[:8].upper()}"
    
    return Delivery(
        delivery_id=delivery_id,
        tracking_number=tracking_number,
        driver_id=driver_id,
        attempt_number=attempt_number,
        delivery_date=datetime.now(),
        delivery_status="Pending"
    )

def record_successful_delivery(
    delivery: Delivery,
    recipient_name: str,
    signature: Optional[str] = None,
    photo_proof: Optional[str] = None,
    delivery_notes: Optional[str] = None,
    gps_coordinates: Optional[tuple[float, float]] = None
) -> Delivery:
    """
    Record a successful delivery with proof
    
    Args:
        delivery: Delivery object
        recipient_name: Name of person who received package
        signature: Digital signature (optional)
        photo_proof: Photo evidence of delivery
        delivery_notes: Additional delivery notes
        gps_coordinates: GPS location of delivery (latitude, longitude)
    
    Returns:
        Updated Delivery object
    """
    delivery.delivery_status = "Successful"
    delivery.recipient_name = recipient_name
    delivery.signature = signature
    delivery.photo_proof = photo_proof
    delivery.delivery_notes = delivery_notes
    delivery.gps_coordinates = gps_coordinates
    delivery.delivery_date = datetime.now()
    
    return delivery

def record_failed_delivery(
    delivery: Delivery,
    failed_reason: str,
    delivery_notes: Optional[str] = None
) -> Delivery:
    """
    Record a failed delivery attempt
    
    Args:
        delivery: Delivery object
        failed_reason: Reason for delivery failure
        delivery_notes: Additional notes about the failure
    
    Returns:
        Updated Delivery object
    """
    delivery.delivery_status = "Failed"
    delivery.failed_reason = failed_reason
    delivery.delivery_notes = delivery_notes
    delivery.delivery_date = datetime.now()
    
    return delivery

def get_delivery_info(delivery: Delivery) -> str:
    """Get formatted delivery information"""
    info = f"""
DT Logistics Delivery Record
=============================
Delivery ID: {delivery.delivery_id}
Tracking Number: {delivery.tracking_number}
Driver ID: {delivery.driver_id}
Attempt Number: {delivery.attempt_number}
Status: {delivery.delivery_status}
Date: {delivery.delivery_date.strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    if delivery.delivery_status == "Successful":
        info += f"""Delivery Details:
  Recipient: {delivery.recipient_name}
  Signature: {'Yes' if delivery.signature else 'No'}
  Photo Proof: {'Yes' if delivery.photo_proof else 'No'}
  GPS Location: {delivery.gps_coordinates if delivery.gps_coordinates else 'Not recorded'}
  Notes: {delivery.delivery_notes or 'None'}
"""
    elif delivery.delivery_status == "Failed":
        info += f"""Failure Details:
  Reason: {delivery.failed_reason}
  Notes: {delivery.delivery_notes or 'None'}
"""
    else:
        info += "Delivery in progress...\n"
    
    return info

def validate_delivery_proof(delivery: Delivery) -> tuple[bool, list[str]]:
    """
    Validate delivery proof requirements
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if delivery.delivery_status == "Successful":
        # Must have recipient name
        if not delivery.recipient_name or len(delivery.recipient_name.strip()) < 2:
            errors.append("Recipient name is required for successful delivery")
        
        # Should have either signature or photo proof
        if not delivery.signature and not delivery.photo_proof:
            errors.append("Either signature or photo proof is required")
        
        # GPS coordinates recommended
        if not delivery.gps_coordinates:
            errors.append("GPS coordinates recommended for delivery verification")
    
    elif delivery.delivery_status == "Failed":
        # Must have failure reason
        if not delivery.failed_reason or len(delivery.failed_reason.strip()) < 5:
            errors.append("Detailed failure reason is required")
    
    return (len(errors) == 0, errors)

# Common delivery failure reasons
DELIVERY_FAILURE_REASONS = [
    "Recipient not home",
    "Address not found",
    "Unsafe location",
    "Access restricted",
    "Business closed",
    "Refused by recipient",
    "Damaged package",
    "Incorrect address",
    "Weather conditions",
    "Security concerns"
]

# Example usage and testing
if __name__ == "__main__":
    print("DT Logistics - Delivery Management Module")
    print("=" * 50)
    
    # Create delivery attempt
    print("\nCreating delivery attempt...")
    delivery = create_delivery_attempt(
        tracking_number="DTVIC12345678",
        driver_id="DRV001",
        attempt_number=1
    )
    
    print(get_delivery_info(delivery))
    
    # Record successful delivery
    print("\nRecording successful delivery...")
    record_successful_delivery(
        delivery,
        recipient_name="John Smith",
        signature="digital_signature_data",
        photo_proof="photo_url_or_data",
        delivery_notes="Left at front door as instructed",
        gps_coordinates=(-37.8136, 144.9631)  # Melbourne coordinates
    )
    
    # Validate delivery
    is_valid, errors = validate_delivery_proof(delivery)
    if is_valid:
        print("✓ Delivery proof validation passed")
    else:
        print("✗ Delivery proof validation issues:")
        for error in errors:
            print(f"  - {error}")
    
    print(get_delivery_info(delivery))
    
    # Test failed delivery
    print("\n" + "=" * 50)
    print("Testing failed delivery...")
    failed_delivery = create_delivery_attempt(
        tracking_number="DTVIC87654321",
        driver_id="DRV001",
        attempt_number=1
    )
    
    record_failed_delivery(
        failed_delivery,
        failed_reason="Recipient not home",
        delivery_notes="Left card in mailbox. Package returned to depot."
    )
    
    print(get_delivery_info(failed_delivery))
