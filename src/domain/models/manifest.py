"""
Domain Model: Manifest

Represents a driver delivery manifest with assigned parcels and route information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class ManifestStatus(str, Enum):
    """Manifest lifecycle statuses"""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ManifestParcel:
    """Parcel reference within a manifest"""
    tracking_number: str
    barcode: str
    recipient_name: str
    recipient_address: str
    delivery_sequence: int
    status: str = "pending"
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None


@dataclass
class Manifest:
    """
    Driver delivery manifest
    
    Represents a collection of parcels assigned to a driver for delivery,
    with route optimization and delivery tracking.
    """
    
    # Identifiers
    id: str
    manifest_id: str  # Business-friendly ID (e.g., "MAN-20250403-001")
    
    # Assignment
    driver_id: str
    driver_name: str
    
    # Manifest metadata
    created_at: datetime
    status: ManifestStatus = ManifestStatus.DRAFT
    
    # Route information
    depot_location: str = "unknown"
    total_parcels: int = 0
    delivered_parcels: int = 0
    failed_parcels: int = 0
    
    # Parcels in this manifest
    parcels: List[ManifestParcel] = field(default_factory=list)
    
    # Optimization data
    optimized_route: List[str] = field(default_factory=list)  # Ordered addresses
    total_distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    notes: str = ""
    created_by: str = "system"
    
    def __post_init__(self):
        """Validate business invariants"""
        if not self.manifest_id:
            raise ValueError("Manifest ID is required")
        if not self.driver_id:
            raise ValueError("Driver ID is required")
        if not self.driver_name:
            raise ValueError("Driver name is required")
        
        # Ensure status is valid enum
        if isinstance(self.status, str):
            self.status = ManifestStatus(self.status)
    
    def add_parcel(self, parcel: ManifestParcel) -> None:
        """Add a parcel to the manifest"""
        if self.status != ManifestStatus.DRAFT:
            raise ValueError("Cannot add parcels to non-draft manifest")
        
        self.parcels.append(parcel)
        self.total_parcels = len(self.parcels)
    
    def activate(self) -> None:
        """Activate the manifest for delivery"""
        if self.status != ManifestStatus.DRAFT:
            raise ValueError("Only draft manifests can be activated")
        if not self.parcels:
            raise ValueError("Cannot activate empty manifest")
        
        self.status = ManifestStatus.ACTIVE
    
    def start_delivery(self) -> None:
        """Mark manifest as in progress"""
        if self.status != ManifestStatus.ACTIVE:
            raise ValueError("Only active manifests can be started")
        
        self.status = ManifestStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
    
    def mark_parcel_delivered(self, tracking_number: str) -> None:
        """Mark a parcel as delivered"""
        for parcel in self.parcels:
            if parcel.tracking_number == tracking_number:
                parcel.status = "delivered"
                parcel.delivered_at = datetime.utcnow()
                self.delivered_parcels += 1
                break
    
    def mark_parcel_failed(self, tracking_number: str, reason: str) -> None:
        """Mark a parcel delivery as failed"""
        for parcel in self.parcels:
            if parcel.tracking_number == tracking_number:
                parcel.status = "failed"
                parcel.notes = reason
                self.failed_parcels += 1
                break
    
    def complete(self) -> None:
        """Complete the manifest"""
        if self.status != ManifestStatus.IN_PROGRESS:
            raise ValueError("Only in-progress manifests can be completed")
        
        self.status = ManifestStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def get_completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_parcels == 0:
            return 0.0
        return (self.delivered_parcels / self.total_parcels) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "id": self.id,
            "manifest_id": self.manifest_id,
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status.value,
            "depot_location": self.depot_location,
            "total_parcels": self.total_parcels,
            "delivered_parcels": self.delivered_parcels,
            "failed_parcels": self.failed_parcels,
            "parcels": [
                {
                    "tracking_number": p.tracking_number,
                    "barcode": p.barcode,
                    "recipient_name": p.recipient_name,
                    "recipient_address": p.recipient_address,
                    "delivery_sequence": p.delivery_sequence,
                    "status": p.status,
                    "delivered_at": p.delivered_at.isoformat() if p.delivered_at else None,
                    "notes": p.notes,
                }
                for p in self.parcels
            ],
            "optimized_route": self.optimized_route,
            "total_distance_km": self.total_distance_km,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "notes": self.notes,
            "created_by": self.created_by,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Manifest":
        """Create Manifest from dictionary (database record)"""
        # Parse datetime fields
        for date_field in ["created_at", "started_at", "completed_at"]:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
        
        # Parse parcel data
        if "parcels" in data and isinstance(data["parcels"], list):
            parcels = []
            for p in data["parcels"]:
                delivered_at = None
                if p.get("delivered_at") and isinstance(p["delivered_at"], str):
                    delivered_at = datetime.fromisoformat(p["delivered_at"].replace('Z', '+00:00'))
                
                parcels.append(ManifestParcel(
                    tracking_number=p["tracking_number"],
                    barcode=p["barcode"],
                    recipient_name=p["recipient_name"],
                    recipient_address=p["recipient_address"],
                    delivery_sequence=p["delivery_sequence"],
                    status=p.get("status", "pending"),
                    delivered_at=delivered_at,
                    notes=p.get("notes"),
                ))
            data["parcels"] = parcels
        
        # Remove any fields not in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
