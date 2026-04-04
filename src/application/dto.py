"""
Data Transfer Objects (DTOs)

DTOs are used to transfer data between layers without exposing domain models.
They provide a clear API contract for application services.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.config.constants import ParcelStatus, ServiceType


@dataclass
class ParcelDTO:
    """Data transfer object for parcel information."""

    tracking_number: str
    sender_name: str
    recipient_name: str
    recipient_address: str
    recipient_postcode: str
    recipient_state: str
    service_type: ServiceType
    current_status: ParcelStatus
    weight_kg: float
    created_at: datetime
    
    # Optional fields
    sender_phone: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    special_instructions: Optional[str] = None
    assigned_driver: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None


@dataclass
class ManifestDTO:
    """Data transfer object for manifest information."""

    manifest_id: str
    driver_id: str
    driver_name: str
    created_at: datetime
    status: str
    parcel_count: int
    completed_items: int
    
    # Optional fields
    depot_name: Optional[str] = None
    route_date: Optional[datetime] = None


@dataclass
class ApprovalRequestDTO:
    """Data transfer object for approval requests."""

    request_id: str
    tracking_number: str
    request_type: str
    status: str
    created_at: datetime
    
    # Optional fields
    requester_name: Optional[str] = None
    reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class UserDTO:
    """Data transfer object for user information."""

    username: str
    role: str
    full_name: str
    
    # Optional fields
    email: Optional[str] = None
    driver_id: Optional[str] = None
    active: bool = True
