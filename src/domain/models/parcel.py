"""
Domain Model: Parcel

Represents a parcel entity in the Zava logistics system.
Contains all parcel-related data and business invariants.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class ParcelStatus(str, Enum):
    """Valid parcel statuses in the system"""
    REGISTERED = "registered"
    AT_DEPOT = "at_depot"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED = "returned"
    HELD = "held"
    CANCELLED = "cancelled"


class ServiceType(str, Enum):
    """Available delivery service types"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    REGISTERED = "registered"


@dataclass
class Parcel:
    """
    Parcel domain model
    
    Represents a single parcel in the logistics network with all associated
    metadata, tracking information, and delivery details.
    """
    
    # Identifiers
    id: str
    barcode: str
    tracking_number: str
    
    # Sender information
    sender_name: str
    sender_address: str
    sender_phone: Optional[str]
    
    # Recipient information
    recipient_name: str
    recipient_address: str
    recipient_phone: Optional[str]
    destination_postcode: str
    destination_state: str
    destination_city: Optional[str] = None
    
    # Service details
    service_type: ServiceType = ServiceType.STANDARD
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    declared_value: Optional[float] = None
    special_instructions: Optional[str] = None
    
    # Location tracking
    store_location: str = "unknown"
    current_location: str = "unknown"
    origin_location: Optional[str] = None
    
    # Status tracking
    current_status: ParcelStatus = ParcelStatus.REGISTERED
    registration_timestamp: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    
    # Delivery information
    delivery_attempts: int = 0
    is_delivered: bool = False
    delivery_timestamp: Optional[datetime] = None
    delivered_by: Optional[str] = None
    signature_captured: Optional[str] = None
    
    # Assignment
    assigned_driver_id: Optional[str] = None
    assigned_driver_name: Optional[str] = None
    assigned_manifest_id: Optional[str] = None
    
    # Risk and compliance
    fraud_risk_score: Optional[int] = None
    requires_approval: bool = False
    approval_status: Optional[str] = None
    
    # Photos and documentation
    lodgement_photos: List[str] = field(default_factory=list)
    delivery_photos: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate business invariants"""
        if not self.barcode:
            raise ValueError("Barcode is required")
        if not self.tracking_number:
            raise ValueError("Tracking number is required")
        if not self.sender_name:
            raise ValueError("Sender name is required")
        if not self.recipient_name:
            raise ValueError("Recipient name is required")
        if not self.recipient_address:
            raise ValueError("Recipient address is required")
        
        # Ensure status is valid enum
        if isinstance(self.current_status, str):
            self.current_status = ParcelStatus(self.current_status)
        
        # Ensure service type is valid enum
        if isinstance(self.service_type, str):
            self.service_type = ServiceType(self.service_type)
    
    def mark_delivered(
        self,
        delivered_by: str,
        signature: Optional[str] = None,
        photo: Optional[str] = None
    ) -> None:
        """Mark parcel as delivered"""
        self.is_delivered = True
        self.current_status = ParcelStatus.DELIVERED
        self.delivery_timestamp = datetime.utcnow()
        self.delivered_by = delivered_by
        if signature:
            self.signature_captured = signature
        if photo:
            self.delivery_photos.append(photo)
    
    def assign_to_driver(self, driver_id: str, driver_name: str, manifest_id: str) -> None:
        """Assign parcel to a driver"""
        self.assigned_driver_id = driver_id
        self.assigned_driver_name = driver_name
        self.assigned_manifest_id = manifest_id
        self.current_status = ParcelStatus.OUT_FOR_DELIVERY
    
    def update_location(self, location: str) -> None:
        """Update current location"""
        self.current_location = location
        
    def add_note(self, note: str) -> None:
        """Add a note to the parcel"""
        self.notes.append(note)
    
    def increment_delivery_attempt(self) -> None:
        """Record a failed delivery attempt"""
        self.delivery_attempts += 1
        if self.delivery_attempts >= 3:
            self.current_status = ParcelStatus.RETURNED
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "id": self.id,
            "barcode": self.barcode,
            "tracking_number": self.tracking_number,
            "sender_name": self.sender_name,
            "sender_address": self.sender_address,
            "sender_phone": self.sender_phone,
            "recipient_name": self.recipient_name,
            "recipient_address": self.recipient_address,
            "recipient_phone": self.recipient_phone,
            "destination_postcode": self.destination_postcode,
            "destination_state": self.destination_state,
            "destination_city": self.destination_city,
            "service_type": self.service_type.value,
            "weight": self.weight,
            "dimensions": self.dimensions,
            "declared_value": self.declared_value,
            "special_instructions": self.special_instructions,
            "store_location": self.store_location,
            "current_location": self.current_location,
            "origin_location": self.origin_location,
            "current_status": self.current_status.value,
            "registration_timestamp": self.registration_timestamp.isoformat() if self.registration_timestamp else None,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "delivery_attempts": self.delivery_attempts,
            "is_delivered": self.is_delivered,
            "delivery_timestamp": self.delivery_timestamp.isoformat() if self.delivery_timestamp else None,
            "delivered_by": self.delivered_by,
            "signature_captured": self.signature_captured,
            "assigned_driver_id": self.assigned_driver_id,
            "assigned_driver_name": self.assigned_driver_name,
            "assigned_manifest_id": self.assigned_manifest_id,
            "fraud_risk_score": self.fraud_risk_score,
            "requires_approval": self.requires_approval,
            "approval_status": self.approval_status,
            "lodgement_photos": self.lodgement_photos,
            "delivery_photos": self.delivery_photos,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Parcel":
        """Create Parcel from dictionary (database record)"""
        # Parse datetime fields
        for date_field in ["registration_timestamp", "estimated_delivery", "delivery_timestamp", "created_at", "updated_at"]:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
        
        # Remove any fields not in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
