"""
Domain Model: Fraud Report

Represents a suspected fraud or security incident report.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class FraudCategory(str, Enum):
    """Categories of fraud threats"""
    PHISHING = "phishing"
    IMPERSONATION = "impersonation"
    PAYMENT_FRAUD = "payment_fraud"
    IDENTITY_THEFT = "identity_theft"
    PARCEL_THEFT = "parcel_theft"
    ACCOUNT_TAKEOVER = "account_takeover"
    SOCIAL_ENGINEERING = "social_engineering"
    OTHER = "other"


class FraudStatus(str, Enum):
    """Fraud report investigation statuses"""
    REPORTED = "reported"
    UNDER_REVIEW = "under_review"
    INVESTIGATING = "investigating"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class RiskLevel(str, Enum):
    """Risk severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudReport:
    """
    Fraud Report domain model
    
    Represents a suspected fraud incident with analysis,
    risk assessment, and investigation tracking.
    """
    
    # Identifiers
    id: str
    report_id: str  # Business-friendly ID
    
    # Incident details
    category: FraudCategory
    description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_score: Optional[int] = None  # 0-100
    
    # Related entities
    tracking_number: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    
    # Evidence
    suspicious_content: Optional[str] = None
    sender_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Status
    status: FraudStatus = FraudStatus.REPORTED
    
    # Reporting
    reported_by: str = "system"
    reported_at: Optional[datetime] = None
    report_source: str = "customer"  # customer, driver, system, agent
    
    # Investigation
    assigned_to: Optional[str] = None
    investigated_by: Optional[str] = None
    investigation_notes: List[str] = field(default_factory=list)
    
    # Actions taken
    actions_taken: List[str] = field(default_factory=list)
    customer_notified: bool = False
    parcel_held: bool = False
    account_flagged: bool = False
    
    # Resolution
    resolved_at: Optional[datetime] = None
    resolution_summary: Optional[str] = None
    
    # AI Analysis
    ai_assessment: Optional[str] = None
    ai_confidence: Optional[float] = None
    detected_patterns: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate business invariants"""
        if not self.report_id:
            raise ValueError("Report ID is required")
        if not self.description:
            raise ValueError("Description is required")
        
        # Ensure enums are valid
        if isinstance(self.category, str):
            self.category = FraudCategory(self.category)
        if isinstance(self.status, str):
            self.status = FraudStatus(self.status)
        if isinstance(self.risk_level, str):
            self.risk_level = RiskLevel(self.risk_level)
        
        # Validate risk score
        if self.risk_score is not None:
            if not (0 <= self.risk_score <= 100):
                raise ValueError("Risk score must be between 0 and 100")
    
    def assign_to_investigator(self, investigator: str) -> None:
        """Assign to an investigator"""
        self.assigned_to = investigator
        self.status = FraudStatus.UNDER_REVIEW
    
    def start_investigation(self, investigator: str) -> None:
        """Begin active investigation"""
        self.investigated_by = investigator
        self.status = FraudStatus.INVESTIGATING
    
    def add_investigation_note(self, note: str) -> None:
        """Add a note to the investigation"""
        self.investigation_notes.append(f"[{datetime.utcnow().isoformat()}] {note}")
    
    def record_action(self, action: str) -> None:
        """Record an action taken"""
        self.actions_taken.append(f"[{datetime.utcnow().isoformat()}] {action}")
    
    def confirm_fraud(self) -> None:
        """Confirm this is a legitimate fraud case"""
        if self.status == FraudStatus.RESOLVED:
            raise ValueError("Cannot confirm already resolved case")
        
        self.status = FraudStatus.CONFIRMED
        self.risk_level = RiskLevel.HIGH
    
    def mark_false_positive(self, reason: str) -> None:
        """Mark as false positive"""
        self.status = FraudStatus.FALSE_POSITIVE
        self.resolution_summary = f"False positive: {reason}"
        self.resolved_at = datetime.utcnow()
    
    def escalate(self, reason: str) -> None:
        """Escalate to higher authority"""
        self.status = FraudStatus.ESCALATED
        self.add_investigation_note(f"ESCALATED: {reason}")
        self.risk_level = RiskLevel.CRITICAL
    
    def resolve(self, summary: str) -> None:
        """Resolve the fraud case"""
        self.status = FraudStatus.RESOLVED
        self.resolution_summary = summary
        self.resolved_at = datetime.utcnow()
    
    def hold_parcel(self) -> None:
        """Mark associated parcel as held"""
        if not self.tracking_number:
            raise ValueError("Cannot hold parcel - no tracking number associated")
        
        self.parcel_held = True
        self.record_action("Parcel held for security review")
    
    def notify_customer(self) -> None:
        """Mark customer as notified"""
        self.customer_notified = True
        self.record_action("Customer notified of security concern")
    
    def requires_urgent_action(self) -> bool:
        """Determine if urgent action is needed"""
        return (
            self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            (self.risk_score is not None and self.risk_score >= 70)
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database storage"""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "category": self.category.value,
            "description": self.description,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "tracking_number": self.tracking_number,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "suspicious_content": self.suspicious_content,
            "sender_info": self.sender_info,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status.value,
            "reported_by": self.reported_by,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "report_source": self.report_source,
            "assigned_to": self.assigned_to,
            "investigated_by": self.investigated_by,
            "investigation_notes": self.investigation_notes,
            "actions_taken": self.actions_taken,
            "customer_notified": self.customer_notified,
            "parcel_held": self.parcel_held,
            "account_flagged": self.account_flagged,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_summary": self.resolution_summary,
            "ai_assessment": self.ai_assessment,
            "ai_confidence": self.ai_confidence,
            "detected_patterns": self.detected_patterns,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FraudReport":
        """Create FraudReport from dictionary (database record)"""
        # Parse datetime fields
        for date_field in ["reported_at", "resolved_at"]:
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
        
        # Remove any fields not in the dataclass
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
