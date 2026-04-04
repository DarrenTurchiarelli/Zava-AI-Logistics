"""
Domain Model: Driver

Represents a delivery driver in the Zava logistics network.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class DriverStatus(str, Enum):
    """Driver availability statuses"""
    AVAILABLE = "available"
    ON_ROUTE = "on_route"
    OFF_DUTY = "off_duty"
    ON_BREAK = "on_break"


@dataclass
class DriverLocation:
    """Driver's current GPS location"""
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: Optional[float] = None  # meters


@dataclass
class Driver:
    """
    Driver domain model
    
    Represents a delivery driver with their profile, status, and performance metrics.
    """
    
    # Identifiers
    id: str
    driver_id: str  # Business-friendly ID (e.g., "DR001")
    
    # Personal information
    full_name: str
    email: str
    phone: str
    
    # Employment details
    employee_id: Optional[str] = None
    depot_location: str = "unknown"
    
    # Status
    status: DriverStatus = DriverStatus.OFF_DUTY
    
    # Current assignment
    current_manifest_id: Optional[str] = None
    parcels_delivered_today: int = 0
    
    # Location tracking
    current_location: Optional[DriverLocation] = None
    last_location_update: Optional[datetime] = None
    
    # Performance metrics
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    average_delivery_time_minutes: Optional[float] = None
    customer_rating: Optional[float] = None
    
    # Capacity and limits
    max_parcels_per_day: int = 50
    vehicle_type: str = "van"
    vehicle_registration: Optional[str] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    is_active: bool = True
    notes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate business invariants"""
        if not self.driver_id:
            raise ValueError("Driver ID is required")
        if not self.full_name:
            raise ValueError("Full name is required")
        if not self.email:
            raise ValueError("Email is required")
        
        # Ensure status is valid enum
        if isinstance(self.status, str):
            self.status = DriverStatus(self.status)
    
    def assign_manifest(self, manifest_id: str) -> None:
        """Assign a manifest to this driver"""
        if self.current_manifest_id:
            raise ValueError(f"Driver already has active manifest: {self.current_manifest_id}")
        
        self.current_manifest_id = manifest_id
        self.status = DriverStatus.ON_ROUTE
    
    def complete_manifest(self) -> None:
        """Mark current manifest as completed"""
        if not self.current_manifest_id:
            raise ValueError("No active manifest to complete")
        
        self.current_manifest_id = None
        self.status = DriverStatus.AVAILABLE
    
    def update_location(self, lat: float, lon: float, accuracy: Optional[float] = None) -> None:
        """Update driver's current location"""
        self.current_location = DriverLocation(
            latitude=lat,
            longitude=lon,
            timestamp=datetime.utcnow(),
            accuracy=accuracy
        )
        self.last_location_update = datetime.utcnow()
    
    def record_delivery(self, success: bool) -> None:
        """Record a delivery outcome"""
        self.total_deliveries += 1
        self.parcels_delivered_today += 1
        
        if success:
            self.successful_deliveries += 1
        else:
            self.failed_deliveries += 1
        
        self.last_active = datetime.utcnow()
    
    def get_success_rate(self) -> float:
        """Calculate delivery success rate"""
        if self.total_deliveries == 0:
            return 0.0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    def is_at_capacity(self) -> bool:
        """Check if driver has reached daily capacity"""
        return self.parcels_delivered_today >= self.max_parcels_per_day
    
    def reset_daily_stats(self) -> None:
        """Reset daily statistics (called at start of day)"""
        self.parcels_delivered_today = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        location_dict = None
        if self.current_location:
            location_dict = {
                "latitude": self.current_location.latitude,
                "longitude": self.current_location.longitude,
                "timestamp": self.current_location.timestamp.isoformat(),
                "accuracy": self.current_location.accuracy,
            }
        
        return {
            "id": self.id,
            "driver_id": self.driver_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "employee_id": self.employee_id,
            "depot_location": self.depot_location,
            "status": self.status.value,
            "current_manifest_id": self.current_manifest_id,
            "parcels_delivered_today": self.parcels_delivered_today,
            "current_location": location_dict,
            "last_location_update": self.last_location_update.isoformat() if self.last_location_update else None,
            "total_deliveries": self.total_deliveries,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
            "average_delivery_time_minutes": self.average_delivery_time_minutes,
            "customer_rating": self.customer_rating,
            "max_parcels_per_day": self.max_parcels_per_day,
            "vehicle_type": self.vehicle_type,
            "vehicle_registration": self.vehicle_registration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "is_active": self.is_active,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Driver":
        """Create Driver from dictionary (database record)"""
        # Parse datetime fields
        for date_field in ["created_at", "last_active", "last_location_update"]:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
        
        # Parse location data
        if data.get("current_location") and isinstance(data["current_location"], dict):
            loc = data["current_location"]
            timestamp = datetime.fromisoformat(loc["timestamp"].replace('Z', '+00:00')) if isinstance(loc.get("timestamp"), str) else datetime.utcnow()
            data["current_location"] = DriverLocation(
                latitude=loc["latitude"],
                longitude=loc["longitude"],
                timestamp=timestamp,
                accuracy=loc.get("accuracy"),
            )
        
        # Remove any fields not in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
