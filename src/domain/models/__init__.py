"""
Domain Models Package

Exports all domain models and enums for easy importing.
"""

from .parcel import Parcel, ParcelStatus, ServiceType
from .manifest import Manifest, ManifestParcel, ManifestStatus
from .driver import Driver, DriverLocation, DriverStatus
from .approval import ApprovalRequest, ApprovalType, ApprovalStatus
from .fraud_report import FraudReport, FraudCategory, FraudStatus, RiskLevel

__all__ = [
    # Parcel
    "Parcel",
    "ParcelStatus",
    "ServiceType",
    # Manifest
    "Manifest",
    "ManifestParcel",
    "ManifestStatus",
    # Driver
    "Driver",
    "DriverLocation",
    "DriverStatus",
    # Approval
    "ApprovalRequest",
    "ApprovalType",
    "ApprovalStatus",
    # Fraud
    "FraudReport",
    "FraudCategory",
    "FraudStatus",
    "RiskLevel",
]
