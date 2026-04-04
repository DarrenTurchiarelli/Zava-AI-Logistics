"""
Domain Model: Approval Request

Represents an approval request for parcel operations requiring authorization.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
from enum import Enum


class ApprovalType(str, Enum):
    """Types of approval requests"""
    DELIVERY_REDIRECT = "delivery_redirect"
    HIGH_VALUE = "high_value"
    FRAUD_REVIEW = "fraud_review"
    CUSTOMS_CLEARANCE = "customs_clearance"
    RETURN_AUTHORIZATION = "return_authorization"
    SPECIAL_HANDLING = "special_handling"


class ApprovalStatus(str, Enum):
    """Approval request statuses"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """
    Approval Request domain model
    
    Represents a request for authorization of special parcel handling,
    high-value deliveries, fraud reviews, or other exceptional cases.
    """
    
    # Identifiers
    id: str
    request_id: str  # Business-friendly ID
    
    # Related entities
    tracking_number: str
    parcel_barcode: str
    
    # Request details
    request_type: ApprovalType
    reason: str
    additional_details: Optional[str] = None
    
    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Requestor
    requested_by: str = "system"
    requested_at: Optional[datetime] = None
    
    # Reviewer
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Urgency
    priority: str = "normal"  # low, normal, high, critical
    expires_at: Optional[datetime] = None
    
    # Risk assessment (for fraud reviews)
    risk_score: Optional[int] = None
    risk_factors: Optional[str] = None
    
    # Financial (for high-value parcels)
    declared_value: Optional[float] = None
    
    # Resolution
    approval_conditions: Optional[str] = None
    
    def __post_init__(self):
        """Validate business invariants"""
        if not self.request_id:
            raise ValueError("Request ID is required")
        if not self.tracking_number:
            raise ValueError("Tracking number is required")
        if not self.reason:
            raise ValueError("Reason is required")
        
        # Ensure enums are valid
        if isinstance(self.request_type, str):
            self.request_type = ApprovalType(self.request_type)
        if isinstance(self.status, str):
            self.status = ApprovalStatus(self.status)
    
    def approve(self, reviewer: str, notes: Optional[str] = None, conditions: Optional[str] = None) -> None:
        """Approve the request"""
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot approve request with status: {self.status}")
        
        self.status = ApprovalStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.review_notes = notes
        self.approval_conditions = conditions
    
    def deny(self, reviewer: str, notes: str) -> None:
        """Deny the request"""
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot deny request with status: {self.status}")
        
        self.status = ApprovalStatus.DENIED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.review_notes = notes
    
    def cancel(self) -> None:
        """Cancel the request"""
        if self.status not in [ApprovalStatus.PENDING]:
            raise ValueError(f"Cannot cancel request with status: {self.status}")
        
        self.status = ApprovalStatus.CANCELLED
    
    def is_expired(self) -> bool:
        """Check if the approval request has expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def check_expiry(self) -> None:
        """Update status if expired"""
        if self.status == ApprovalStatus.PENDING and self.is_expired():
            self.status = ApprovalStatus.EXPIRED
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "tracking_number": self.tracking_number,
            "parcel_barcode": self.parcel_barcode,
            "request_type": self.request_type.value,
            "reason": self.reason,
            "additional_details": self.additional_details,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "priority": self.priority,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "risk_score": self.risk_score,
            "risk_factors": self.risk_factors,
            "declared_value": self.declared_value,
            "approval_conditions": self.approval_conditions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ApprovalRequest":
        """Create ApprovalRequest from dictionary (database record)"""
        # Parse datetime fields
        for date_field in ["requested_at", "reviewed_at", "expires_at"]:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
        
        # Remove any fields not in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
