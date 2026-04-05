"""
Application Constants and Enumerations

This module defines all constants, enums, and static values used throughout
the application. Using enums provides type safety and prevents typos.

Usage:
    from src.config.constants import ParcelStatus, UserRole, ServiceType

    if parcel.status == ParcelStatus.IN_TRANSIT:
        # Handle in-transit parcel
        pass
"""

from enum import Enum


class ParcelStatus(str, Enum):
    """Parcel status throughout the delivery lifecycle."""

    # Initial states
    PENDING = "pending"
    REGISTERED = "registered"
    READY_FOR_COLLECTION = "ready_for_collection"

    # In transit states
    AT_DEPOT = "at_depot"
    IN_TRANSIT = "in_transit"
    AT_SORTING_FACILITY = "at_sorting_facility"

    # Delivery states
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"

    # Exception states
    EXCEPTION = "exception"
    HELD = "held"
    RETURNED_TO_SENDER = "returned_to_sender"
    DAMAGED = "damaged"
    LOST = "lost"

    def __str__(self) -> str:
        """Return human-readable status."""
        return self.value.replace("_", " ").title()

    @property
    def is_delivered(self) -> bool:
        """Check if parcel has been delivered."""
        return self in (self.DELIVERED, self.RETURNED_TO_SENDER)

    @property
    def is_exception(self) -> bool:
        """Check if parcel is in an exception state."""
        return self in (self.EXCEPTION, self.HELD, self.DAMAGED, self.LOST)

    @property
    def is_active(self) -> bool:
        """Check if parcel is actively being processed."""
        return not (self.is_delivered or self.is_exception)


class UserRole(str, Enum):
    """User roles for access control."""

    ADMIN = "admin"
    DRIVER = "driver"
    DEPOT_MANAGER = "depot_manager"
    CUSTOMER_SERVICE = "customer_service"
    GUEST = "guest"

    def __str__(self) -> str:
        """Return human-readable role."""
        return self.value.replace("_", " ").title()

    @property
    def permissions(self) -> set[str]:
        """Get permissions for this role."""
        role_permissions = {
            self.ADMIN: {"read", "write", "delete", "manage_users", "view_reports", "approve_requests"},
            self.DEPOT_MANAGER: {"read", "write", "approve_requests", "view_reports", "manage_manifests"},
            self.DRIVER: {"read", "update_delivery", "view_manifest"},
            self.CUSTOMER_SERVICE: {"read", "create_request", "chat_agent"},
            self.GUEST: {"read_public"},
        }
        return role_permissions.get(self, set())


class ServiceType(str, Enum):
    """Delivery service types."""

    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"
    REGISTERED = "registered"
    ECONOMY = "economy"
    PRIORITY = "priority"

    def __str__(self) -> str:
        """Return human-readable service type."""
        return self.value.title()

    @property
    def estimated_days(self) -> int:
        """Get estimated delivery days for this service type."""
        days_map = {
            self.OVERNIGHT: 1,
            self.EXPRESS: 2,
            self.PRIORITY: 3,
            self.STANDARD: 5,
            self.REGISTERED: 5,
            self.ECONOMY: 7,
        }
        return days_map.get(self, 5)

    @property
    def is_premium(self) -> bool:
        """Check if this is a premium service."""
        return self in (self.OVERNIGHT, self.EXPRESS, self.PRIORITY, self.REGISTERED)


class ScanType(str, Enum):
    """Scan types for tracking events."""

    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    PROCESSING = "processing"
    LOADING = "loading"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    PICKUP = "pickup"
    SORTING = "sorting"

    def __str__(self) -> str:
        """Return human-readable scan type."""
        return self.value.title()


class ApprovalStatus(str, Enum):
    """Approval request statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return human-readable approval status."""
        return self.value.title()

    @property
    def is_final(self) -> bool:
        """Check if this is a final status (no further changes allowed)."""
        return self in (self.APPROVED, self.DENIED, self.CANCELLED)


class ApprovalType(str, Enum):
    """Types of approval requests."""

    DELIVERY_REDIRECT = "delivery_redirect"
    LATE_PICKUP = "late_pickup"
    DAMAGE_CLAIM = "damage_claim"
    REFUND_REQUEST = "refund_request"
    ADDRESS_CHANGE = "address_change"
    DELIVERY_INSTRUCTION = "delivery_instruction"
    FRAUD_INVESTIGATION = "fraud_investigation"

    def __str__(self) -> str:
        """Return human-readable approval type."""
        return self.value.replace("_", " ").title()


class FraudRiskLevel(str, Enum):
    """Fraud risk levels from fraud detection agent."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __str__(self) -> str:
        """Return human-readable risk level."""
        return self.value.upper()

    @property
    def requires_review(self) -> bool:
        """Check if this risk level requires manual review."""
        return self in (self.HIGH, self.CRITICAL)

    @property
    def auto_hold(self) -> bool:
        """Check if parcels should be automatically held."""
        return self == self.CRITICAL

    @classmethod
    def from_score(cls, score: float) -> "FraudRiskLevel":
        """
        Convert numeric fraud score to risk level.

        Args:
            score: Fraud risk score (0-100)

        Returns:
            FraudRiskLevel enum value
        """
        if score >= 90:
            return cls.CRITICAL
        elif score >= 70:
            return cls.HIGH
        elif score >= 40:
            return cls.MEDIUM
        else:
            return cls.LOW


class ManifestStatus(str, Enum):
    """Driver manifest statuses."""

    DRAFT = "draft"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        """Return human-readable manifest status."""
        return self.value.replace("_", " ").title()

    @property
    def is_active(self) -> bool:
        """Check if manifest is actively being worked on."""
        return self in (self.ASSIGNED, self.IN_PROGRESS)


class AgentType(str, Enum):
    """Azure AI Foundry agent types."""

    CUSTOMER_SERVICE = "customer_service"
    FRAUD_DETECTION = "fraud_detection"
    IDENTITY_VERIFICATION = "identity_verification"
    DISPATCHER = "dispatcher"
    PARCEL_INTAKE = "parcel_intake"
    SORTING_FACILITY = "sorting_facility"
    DELIVERY_COORDINATION = "delivery_coordination"
    OPTIMIZATION = "optimization"
    DRIVER = "driver"

    def __str__(self) -> str:
        """Return human-readable agent type."""
        return self.value.replace("_", " ").title()

    @property
    def display_name(self) -> str:
        """Get formatted display name for the agent."""
        names = {
            self.CUSTOMER_SERVICE: "Customer Service Agent",
            self.FRAUD_DETECTION: "Fraud Detection Agent",
            self.IDENTITY_VERIFICATION: "Identity Verification Agent",
            self.DISPATCHER: "Dispatcher Agent",
            self.PARCEL_INTAKE: "Parcel Intake Agent",
            self.SORTING_FACILITY: "Sorting Facility Agent",
            self.DELIVERY_COORDINATION: "Delivery Coordination Agent",
            self.OPTIMIZATION: "Optimization Agent",
            self.DRIVER: "Driver Agent",
        }
        return names.get(self, str(self))


class DocumentType(str, Enum):
    """Document types in Cosmos DB containers."""

    PARCEL = "parcel"
    TRACKING_EVENT = "tracking_event"
    DELIVERY_ATTEMPT = "delivery_attempt"
    MANIFEST = "manifest"
    USER = "user"
    APPROVAL_REQUEST = "approval_request"
    FRAUD_REPORT = "fraud_report"
    FEEDBACK = "feedback"
    COMPANY_INFO = "company_info"
    ADDRESS_HISTORY = "address_history"

    def __str__(self) -> str:
        """Return human-readable document type."""
        return self.value.replace("_", " ").title()


class EventType(str, Enum):
    """Event types for audit logging and tracking."""

    PARCEL_REGISTERED = "parcel_registered"
    PARCEL_SCANNED = "parcel_scanned"
    PARCEL_DELIVERED = "parcel_delivered"
    PARCEL_EXCEPTION = "parcel_exception"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    FRAUD_DETECTED = "fraud_detected"
    MANIFEST_CREATED = "manifest_created"
    MANIFEST_ASSIGNED = "manifest_assigned"
    DRIVER_DEPARTED = "driver_departed"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"

    def __str__(self) -> str:
        """Return human-readable event type."""
        return self.value.replace("_", " ").title()


class AustralianState(str, Enum):
    """Australian states and territories."""

    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    SA = "SA"
    WA = "WA"
    TAS = "TAS"
    ACT = "ACT"
    NT = "NT"

    def __str__(self) -> str:
        """Return state code."""
        return self.value

    @property
    def full_name(self) -> str:
        """Get full state name."""
        names = {
            self.NSW: "New South Wales",
            self.VIC: "Victoria",
            self.QLD: "Queensland",
            self.SA: "South Australia",
            self.WA: "Western Australia",
            self.TAS: "Tasmania",
            self.ACT: "Australian Capital Territory",
            self.NT: "Northern Territory",
        }
        return names.get(self, self.value)


# Container names for Cosmos DB
class CosmosContainer(str, Enum):
    """Cosmos DB container names."""

    PARCELS = "parcels"
    TRACKING_EVENTS = "tracking_events"
    DELIVERY_ATTEMPTS = "delivery_attempts"
    MANIFESTS = "driver_manifests"
    USERS = "users"
    APPROVAL_REQUESTS = "approval_requests"
    FRAUD_REPORTS = "fraud_reports"
    FEEDBACK = "feedback"
    COMPANY_INFO = "company_info"
    ADDRESS_HISTORY = "address_history"

    def __str__(self) -> str:
        """Return container name."""
        return self.value


# HTTP Status codes for API responses
class HTTPStatus:
    """Common HTTP status codes."""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# Default values and limits
class Defaults:
    """Default values and system limits."""

    # Pagination
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # Parcel settings
    DEFAULT_SERVICE_TYPE = ServiceType.STANDARD
    MAX_PARCEL_WEIGHT_KG = 30.0
    MIN_TRACKING_NUMBER_LENGTH = 8
    MAX_TRACKING_NUMBER_LENGTH = 20

    # Approval settings
    APPROVAL_TIMEOUT_DAYS = 7
    AUTO_APPROVE_THRESHOLD = 10  # Risk score below this auto-approves
    AUTO_DENY_THRESHOLD = 90  # Risk score above this auto-denies

    # Agent settings
    AGENT_TIMEOUT_SECONDS = 30
    MAX_AGENT_RETRIES = 3

    # Driver manifest
    MAX_PARCELS_PER_MANIFEST = 50
    DEFAULT_MANIFEST_PRIORITY = 1

    # Fraud detection
    FRAUD_HOLD_THRESHOLD = 90  # Fraud score threshold for automatic hold
    FRAUD_REVIEW_THRESHOLD = 70  # Fraud score threshold for manual review


# Validation patterns
class ValidationPattern:
    """Regex patterns for data validation."""

    # Australian phone number (mobile and landline)
    PHONE_AU = r"^(\+?61|0)[2-478](?:[ -]?[0-9]){8}$"

    # Australian postcode
    POSTCODE_AU = r"^(0[289][0-9]{2}|[1-9][0-9]{3})$"

    # Tracking number (alphanumeric, 8-20 chars)
    TRACKING_NUMBER = r"^[A-Z0-9]{8,20}$"

    # Email (basic validation)
    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    # Driver ID
    DRIVER_ID = r"^driver[_-]?\d{3}$"

    # Barcode (alphanumeric)
    BARCODE = r"^[A-Z0-9]+$"
