"""
Repository Package Initialization

Exports all repository interfaces and implementations.
"""

from .base_repository import IRepository, IQueryableRepository
from .parcel_repository import IParcelRepository, CosmosParcelRepository
from .manifest_repository import IManifestRepository, CosmosManifestRepository
from .user_repository import IUserRepository, CosmosUserRepository, User
from .approval_repository import IApprovalRepository, CosmosApprovalRepository

# Export implementation classes as simpler names for convenience
ParcelRepository = CosmosParcelRepository
ManifestRepository = CosmosManifestRepository
ApprovalRepository = CosmosApprovalRepository
UserRepository = CosmosUserRepository

__all__ = [
    "IRepository",
    "IQueryableRepository",
    "IParcelRepository",
    "CosmosParcelRepository",
    "ParcelRepository",
    "IManifestRepository",
    "CosmosManifestRepository",
    "ManifestRepository",
    "IUserRepository",
    "CosmosUserRepository",
    "UserRepository",
    "User",
    "IApprovalRepository",
    "CosmosApprovalRepository",
    "ApprovalRepository",
]

