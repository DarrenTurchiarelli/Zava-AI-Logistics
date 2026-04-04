"""
Zava - Parcel Service
Domain Service: Handles parcel business logic and operations

Extracted from legacy logistics_parcel.py module.
Provides centralized business logic for parcel management.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from src.domain.models.parcel import Parcel


class ParcelService:
    """Domain service for parcel-related business logic"""

    # Australian postcode ranges for state detection
    POSTCODE_RANGES = {
        "NSW": [(1000, 2599), (2619, 2899), (2921, 2999)],
        "ACT": [(200, 299), (2600, 2618), (2900, 2920)],
        "VIC": [(3000, 3999), (8000, 8999)],
        "QLD": [(4000, 4999), (9000, 9999)],
        "SA": [(5000, 5999)],
        "WA": [(6000, 6797), (6800, 6999)],
        "TAS": [(7000, 7999)],
        "NT": [(800, 899)],
    }

    # Valid parcel status values
    VALID_STATUSES = [
        "Registered",
        "In Transit",
        "At Sorting Facility",
        "Out for Delivery",
        "Delivered",
        "Failed Delivery",
        "Returned to Sender",
        "At Depot",
        "Ready for Pickup",
    ]

    # Weight limits (kg)
    MAX_WEIGHT_KG = 30.0
    MIN_WEIGHT_KG = 0.0

    @classmethod
    def get_state_from_postcode(cls, postcode: str) -> str:
        """
        Determine Australian state from postcode using accurate range mapping

        Args:
            postcode: Australian postcode (numeric string)

        Returns:
            State code (e.g., "NSW", "VIC") or "UNKNOWN"/"INVALID"
        """
        try:
            pc = int(postcode)

            for state, ranges in cls.POSTCODE_RANGES.items():
                for min_pc, max_pc in ranges:
                    if min_pc <= pc <= max_pc:
                        return state

            return "UNKNOWN"

        except ValueError:
            return "INVALID"

    @classmethod
    def generate_tracking_number(cls, state: str) -> str:
        """
        Generate a unique tracking number with state prefix

        Format: DT{STATE}{8-CHAR-UUID}
        Example: DTNSWABC12345

        Args:
            state: Australian state code (e.g., "NSW", "VIC")

        Returns:
            Unique tracking number
        """
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"DT{state}{unique_id}"

    @classmethod
    def validate_parcel_data(cls, parcel: Parcel) -> Tuple[bool, List[str]]:
        """
        Validate parcel data for completeness and accuracy

        Args:
            parcel: Parcel object to validate

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
        if parcel.weight_kg <= cls.MIN_WEIGHT_KG:
            errors.append("Weight must be greater than 0 kg")
        elif parcel.weight_kg > cls.MAX_WEIGHT_KG:
            errors.append(f"Weight exceeds maximum limit of {cls.MAX_WEIGHT_KG} kg (contact freight department)")

        return (len(errors) == 0, errors)

    @classmethod
    def validate_status_transition(cls, current_status: str, new_status: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a status transition is allowed

        Args:
            current_status: Current parcel status
            new_status: Desired new status

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if statuses are valid
        if new_status not in cls.VALID_STATUSES:
            return False, f"Invalid status: {new_status}. Must be one of {cls.VALID_STATUSES}"

        # Define allowed transitions
        allowed_transitions = {
            "Registered": ["In Transit", "At Depot", "At Sorting Facility"],
            "At Depot": ["In Transit", "Ready for Pickup", "At Sorting Facility"],
            "Ready for Pickup": ["Out for Delivery", "At Sorting Facility"],
            "In Transit": ["At Sorting Facility", "Out for Delivery", "Delivered", "Failed Delivery"],
            "At Sorting Facility": ["In Transit", "Out for Delivery", "At Depot"],
            "Out for Delivery": ["Delivered", "Failed Delivery", "At Depot"],
            "Delivered": [],  # Terminal state
            "Failed Delivery": ["At Depot", "Out for Delivery", "Returned to Sender"],
            "Returned to Sender": [],  # Terminal state
        }

        if current_status not in allowed_transitions:
            return True, None  # Unknown current status, allow transition

        allowed = allowed_transitions[current_status]
        if new_status in allowed:
            return True, None

        return False, f"Cannot transition from {current_status} to {new_status}"

    @classmethod
    def update_parcel_status(cls, parcel: Parcel, new_status: str, driver_id: Optional[str] = None) -> Parcel:
        """
        Update parcel status with automatic timestamp management

        Args:
            parcel: Parcel object to update
            new_status: New status to set
            driver_id: Driver ID (for assignment-related status changes)

        Returns:
            Updated parcel object

        Raises:
            ValueError: If status transition is invalid
        """
        # Validate status transition
        is_valid, error_msg = cls.validate_status_transition(parcel.status, new_status)
        if not is_valid:
            raise ValueError(error_msg)

        parcel.status = new_status

        # Automatic timestamp management
        if new_status == "Out for Delivery":
            parcel.out_for_delivery_timestamp = datetime.utcnow().isoformat()
            if driver_id:
                parcel.driver_assigned = driver_id

        if new_status == "Delivered":
            parcel.delivery_timestamp = datetime.utcnow().isoformat()

        return parcel

    @classmethod
    def get_parcel_display_info(cls, parcel: Parcel) -> str:
        """
        Get formatted parcel information for display

        Args:
            parcel: Parcel object

        Returns:
            Formatted string with parcel details
        """
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
  Service Type: {parcel.service_type}
  Weight: {parcel.weight_kg} kg
  Dimensions: {parcel.dimensions or 'Not specified'}
  Special Instructions: {parcel.special_instructions or 'None'}

Tracking:
  Created: {parcel.created_timestamp or 'N/A'}
  Driver: {parcel.driver_assigned or 'Not assigned'}
  Out for Delivery: {parcel.out_for_delivery_timestamp or 'Not started'}
  Delivered: {parcel.delivery_timestamp or 'Not delivered'}
"""
        return info

    @classmethod
    def calculate_risk_score(cls, parcel: Parcel) -> int:
        """
        Calculate basic risk score for a parcel (0-100)

        Factors considered:
        - High value parcels
        - Unusual patterns
        - Address issues

        Args:
            parcel: Parcel to assess

        Returns:
            Risk score (0-100, where higher is more risky)
        """
        risk_score = 0

        # High value increases risk
        if hasattr(parcel, "declared_value") and parcel.declared_value:
            if parcel.declared_value > 1000:
                risk_score += 30
            elif parcel.declared_value > 500:
                risk_score += 15

        # Missing or incomplete information increases risk
        if not parcel.special_instructions:
            risk_score += 5

        # Same-day or express service can indicate fraud attempts
        if hasattr(parcel, "service_type") and parcel.service_type:
            if "express" in parcel.service_type.lower():
                risk_score += 10

        # Weight anomalies
        if parcel.weight_kg < 0.1:  # Suspiciously light
            risk_score += 20
        elif parcel.weight_kg > 25:  # Very heavy
            risk_score += 15

        return min(risk_score, 100)
