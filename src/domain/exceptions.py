"""
Domain Exceptions

Custom exceptions for domain-level business logic errors.
"""


class DomainException(Exception):
    """Base exception for all domain errors"""
    pass


class ValidationError(DomainException):
    """Raised when domain validation fails"""
    pass


class EntityNotFoundError(DomainException):
    """Raised when a requested entity doesn't exist"""
    
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} not found: {identifier}")


class DuplicateEntityError(DomainException):
    """Raised when attempting to create a duplicate entity"""
    
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"Duplicate {entity_type}: {identifier} already exists")


class BusinessRuleViolation(DomainException):
    """Raised when a business rule is violated"""
    pass


class InvalidStatusTransition(BusinessRuleViolation):
    """Raised when an invalid status transition is attempted"""
    
    def __init__(self, entity_type: str, from_status: str, to_status: str):
        self.entity_type = entity_type
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid {entity_type} status transition from {from_status} to {to_status}"
        )


class CapacityExceeded(BusinessRuleViolation):
    """Raised when capacity limits are exceeded"""
    
    def __init__(self, resource: str, current: int, maximum: int):
        self.resource = resource
        self.current = current
        self.maximum = maximum
        super().__init__(
            f"{resource} capacity exceeded: {current}/{maximum}"
        )


class UnauthorizedOperation(DomainException):
    """Raised when an operation is attempted without proper authorization"""
    
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(f"Unauthorized operation '{operation}': {reason}")


class ParcelException(DomainException):
    """Base exception for parcel-related errors"""
    pass


class ParcelAlreadyDelivered(ParcelException):
    """Raised when attempting to modify a delivered parcel"""
    
    def __init__(self, tracking_number: str):
        super().__init__(f"Parcel {tracking_number} has already been delivered")


class ManifestException(DomainException):
    """Base exception for manifest-related errors"""
    pass


class ManifestNotEditable(ManifestException):
    """Raised when attempting to edit a non-draft manifest"""
    
    def __init__(self, manifest_id: str, status: str):
        super().__init__(
            f"Manifest {manifest_id} cannot be edited (status: {status})"
        )


class DriverException(DomainException):
    """Base exception for driver-related errors"""
    pass


class DriverUnavailable(DriverException):
    """Raised when a driver is not available for assignment"""
    
    def __init__(self, driver_id: str, reason: str):
        super().__init__(f"Driver {driver_id} is unavailable: {reason}")


class ApprovalException(DomainException):
    """Base exception for approval-related errors"""
    pass


class ApprovalExpired(ApprovalException):
    """Raised when an approval request has expired"""
    
    def __init__(self, request_id: str):
        super().__init__(f"Approval request {request_id} has expired")


class FraudException(DomainException):
    """Base exception for fraud-related errors"""
    pass


class HighRiskOperation(FraudException):
    """Raised when an operation is blocked due to high fraud risk"""
    
    def __init__(self, operation: str, risk_score: int):
        super().__init__(
            f"Operation '{operation}' blocked due to high risk score: {risk_score}%"
        )
