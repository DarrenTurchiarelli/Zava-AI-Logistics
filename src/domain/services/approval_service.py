"""
Zava - Approval Service
Domain Service: Handles approval request processing and validation

Provides centralized business logic for approval operations.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.domain.models.approval import ApprovalRequest, ApprovalStatus, ApprovalType
from src.domain.models.parcel import Parcel


class ApprovalService:
    """Domain service for approval-related business logic"""

    # Approval thresholds and limits
    HIGH_VALUE_THRESHOLD = 500.0  # AUD
    HIGH_RISK_THRESHOLD = 70  # Risk score %
    LOW_RISK_THRESHOLD = 10  # Risk score %
    AUTO_APPROVE_TIMEOUT_HOURS = 24  # Auto-approve after this time if no action
    MAX_PENDING_DAYS = 7  # Maximum days an approval can stay pending

    # Priority levels for approval requests
    PRIORITY_CRITICAL = 1
    PRIORITY_HIGH = 2
    PRIORITY_MEDIUM = 3
    PRIORITY_LOW = 4

    @classmethod
    def determine_approval_priority(cls, request: ApprovalRequest, parcel: Optional[Parcel] = None) -> int:
        """
        Determine priority level for an approval request

        Args:
            request: ApprovalRequest object
            parcel: Associated parcel (if applicable)

        Returns:
            Priority level (1=critical, 2=high, 3=medium, 4=low)
        """
        # Critical priority
        if request.request_type == ApprovalType.FRAUD_ALERT:
            return cls.PRIORITY_CRITICAL

        if request.request_type == ApprovalType.REGULATORY_COMPLIANCE:
            return cls.PRIORITY_CRITICAL

        # High priority
        if parcel and hasattr(parcel, "declared_value"):
            if parcel.declared_value and parcel.declared_value > cls.HIGH_VALUE_THRESHOLD * 2:
                return cls.PRIORITY_HIGH

        if parcel and hasattr(parcel, "fraud_risk_score"):
            if parcel.fraud_risk_score and parcel.fraud_risk_score >= 85:
                return cls.PRIORITY_HIGH

        if request.request_type == ApprovalType.HIGH_VALUE_PARCEL:
            return cls.PRIORITY_HIGH

        # Medium priority
        if request.request_type in [ApprovalType.ADDRESS_CHANGE, ApprovalType.ROUTE_DEVIATION]:
            return cls.PRIORITY_MEDIUM

        # Low priority
        return cls.PRIORITY_LOW

    @classmethod
    def can_auto_approve(cls, request: ApprovalRequest, parcel: Optional[Parcel] = None) -> Tuple[bool, str]:
        """
        Determine if an approval request can be automatically approved

        Args:
            request: ApprovalRequest object
            parcel: Associated parcel (if applicable)

        Returns:
            Tuple of (can_auto_approve, reason)
        """
        # Never auto-approve fraud alerts
        if request.request_type == ApprovalType.FRAUD_ALERT:
            return False, "Fraud alerts require manual review"

        # Never auto-approve regulatory compliance
        if request.request_type == ApprovalType.REGULATORY_COMPLIANCE:
            return False, "Regulatory compliance requires manual review"

        # Check parcel-specific criteria
        if parcel:
            # Low risk, low value parcels can be auto-approved
            if hasattr(parcel, "fraud_risk_score") and parcel.fraud_risk_score:
                if parcel.fraud_risk_score >= cls.HIGH_RISK_THRESHOLD:
                    return False, f"Risk score too high ({parcel.fraud_risk_score}%)"

            # High value parcels need manual approval
            if hasattr(parcel, "declared_value") and parcel.declared_value:
                if parcel.declared_value > cls.HIGH_VALUE_THRESHOLD:
                    return False, f"Value exceeds threshold (${parcel.declared_value})"

        # Check request age for timeout auto-approval
        if request.created_timestamp:
            created = datetime.fromisoformat(request.created_timestamp)
            hours_pending = (datetime.utcnow() - created).total_seconds() / 3600

            if hours_pending > cls.AUTO_APPROVE_TIMEOUT_HOURS:
                return True, f"Auto-approved after {cls.AUTO_APPROVE_TIMEOUT_HOURS}h pending"

        # Default: can auto-approve for low-risk cases
        if request.request_type in [ApprovalType.MINOR_CHANGE, ApprovalType.CUSTOMER_REQUEST]:
            return True, "Low-risk request type"

        return False, "Requires manual review"

    @classmethod
    def can_auto_deny(cls, request: ApprovalRequest, parcel: Optional[Parcel] = None) -> Tuple[bool, str]:
        """
        Determine if an approval request should be automatically denied

        Args:
            request: ApprovalRequest object
            parcel: Associated parcel (if applicable)

        Returns:
            Tuple of (should_auto_deny, reason)
        """
        # Check for critical fraud indicators
        if parcel and hasattr(parcel, "fraud_risk_score") and parcel.fraud_risk_score:
            if parcel.fraud_risk_score >= 90:
                return True, f"Critical fraud risk ({parcel.fraud_risk_score}%)"

        # Check for blacklisted addresses (would need additional data)
        # if parcel and parcel.recipient_address in BLACKLIST:
        #     return True, "Blacklisted address"

        # Check for duplicate requests
        # if request.is_duplicate():
        #     return True, "Duplicate request"

        # Check for missing required documentation
        if request.request_type == ApprovalType.REGULATORY_COMPLIANCE:
            if not request.details or len(request.details) < 20:
                return True, "Insufficient compliance documentation"

        return False, ""

    @classmethod
    def validate_approval_transition(
        cls, current_status: ApprovalStatus, new_status: ApprovalStatus
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that an approval status transition is allowed

        Args:
            current_status: Current approval status
            new_status: Desired new status

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Define allowed transitions
        allowed_transitions = {
            ApprovalStatus.PENDING: [ApprovalStatus.APPROVED, ApprovalStatus.DENIED, ApprovalStatus.CANCELLED],
            ApprovalStatus.APPROVED: [ApprovalStatus.CANCELLED],  # Can cancel approved requests
            ApprovalStatus.DENIED: [],  # Terminal state
            ApprovalStatus.CANCELLED: [],  # Terminal state
        }

        if current_status not in allowed_transitions:
            return False, f"Unknown current status: {current_status}"

        allowed = allowed_transitions[current_status]
        if new_status in allowed:
            return True, None

        return False, f"Cannot transition from {current_status} to {new_status}"

    @classmethod
    def calculate_approval_metrics(cls, requests: List[ApprovalRequest]) -> Dict[str, any]:
        """
        Calculate metrics for a list of approval requests

        Args:
            requests: List of approval requests

        Returns:
            Dictionary of metrics
        """
        if not requests:
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "denied": 0,
                "cancelled": 0,
                "approval_rate": 0.0,
                "avg_processing_time_hours": 0.0,
            }

        total = len(requests)
        pending = sum(1 for r in requests if r.status == ApprovalStatus.PENDING)
        approved = sum(1 for r in requests if r.status == ApprovalStatus.APPROVED)
        denied = sum(1 for r in requests if r.status == ApprovalStatus.DENIED)
        cancelled = sum(1 for r in requests if r.status == ApprovalStatus.CANCELLED)

        # Calculate approval rate (approved / (approved + denied))
        processed = approved + denied
        approval_rate = (approved / processed * 100) if processed > 0 else 0.0

        # Calculate average processing time for completed requests
        processing_times = []
        for request in requests:
            if request.status in [ApprovalStatus.APPROVED, ApprovalStatus.DENIED]:
                if request.created_timestamp and request.updated_timestamp:
                    created = datetime.fromisoformat(request.created_timestamp)
                    updated = datetime.fromisoformat(request.updated_timestamp)
                    hours = (updated - created).total_seconds() / 3600
                    processing_times.append(hours)

        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "denied": denied,
            "cancelled": cancelled,
            "approval_rate": round(approval_rate, 1),
            "avg_processing_time_hours": round(avg_processing_time, 1),
        }

    @classmethod
    def get_overdue_requests(cls, requests: List[ApprovalRequest]) -> List[ApprovalRequest]:
        """
        Get approval requests that are overdue (pending > MAX_PENDING_DAYS)

        Args:
            requests: List of approval requests

        Returns:
            List of overdue requests
        """
        overdue = []
        cutoff_date = datetime.utcnow() - timedelta(days=cls.MAX_PENDING_DAYS)

        for request in requests:
            if request.status == ApprovalStatus.PENDING and request.created_timestamp:
                created = datetime.fromisoformat(request.created_timestamp)
                if created < cutoff_date:
                    overdue.append(request)

        return overdue

    @classmethod
    def format_approval_summary(cls, request: ApprovalRequest) -> str:
        """
        Format approval request for display

        Args:
            request: ApprovalRequest object

        Returns:
            Formatted summary string
        """
        summary = f"""
Approval Request: {request.id}
================================
Type: {request.request_type}
Status: {request.status}
Priority: {cls.determine_approval_priority(request)}

Related Entity:
  Parcel: {request.parcel_id or 'N/A'}

Details:
  {request.details or 'No additional details'}

Requested By: {request.requested_by}
Created: {request.created_timestamp}
Updated: {request.updated_timestamp or 'Not yet processed'}

Reviewer: {request.reviewed_by or 'Pending assignment'}
Decision Notes: {request.decision_notes or 'N/A'}
"""
        return summary

    @classmethod
    def validate_approval_request(cls, request: ApprovalRequest) -> Tuple[bool, List[str]]:
        """
        Validate an approval request for completeness

        Args:
            request: ApprovalRequest to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not request.request_type:
            errors.append("Request type is required")

        if not request.requested_by:
            errors.append("Requester is required")

        if not request.parcel_id:
            errors.append("Associated parcel ID is required")

        if not request.details or len(request.details.strip()) < 10:
            errors.append("Detailed explanation is required (minimum 10 characters)")

        # Validate status
        if request.status not in [e.value for e in ApprovalStatus]:
            errors.append(f"Invalid status: {request.status}")

        return (len(errors) == 0, errors)
