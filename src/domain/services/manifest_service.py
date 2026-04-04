"""
Zava - Manifest Service
Domain Service: Handles manifest generation and driver assignment logic

Extracted from agents/manifest.py module.
Provides centralized business logic for manifest operations.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.domain.models.manifest import Manifest
from src.domain.models.parcel import Parcel


@dataclass
class Driver:
    """Driver information and capacity"""

    driver_id: str
    name: str
    max_capacity: int = 20
    current_load: int = 0
    shift_start: str = "08:00"
    shift_end: str = "18:00"
    location: str = ""
    performance_score: float = 0.85  # Historical performance 0-1
    assigned_parcels: List[str] = field(default_factory=list)

    @property
    def remaining_capacity(self) -> int:
        return self.max_capacity - self.current_load

    @property
    def utilization_rate(self) -> float:
        return self.current_load / self.max_capacity if self.max_capacity > 0 else 0


@dataclass
class ManifestParcel:
    """Parcel prepared for manifest assignment"""

    parcel_id: str
    tracking_number: str
    recipient_address: str
    postcode: str
    delivery_priority: int  # 1=urgent, 2=standard, 3=economy
    estimated_delivery_time_min: int
    special_instructions: Optional[str] = None
    requires_signature: bool = False
    value_dollars: float = 0.0
    coordinates: Optional[Tuple[float, float]] = None


@dataclass
class OptimizedManifest:
    """Generated manifest for a driver"""

    manifest_id: str
    driver_id: str
    driver_name: str
    date: str
    parcels: List[ManifestParcel]
    total_parcels: int
    optimized_route: List[str]
    estimated_distance_km: float
    estimated_duration_min: int
    estimated_completion_time: str
    workload_score: float  # 0-1, with 1 being fully utilized
    route_efficiency_score: float  # 0-1, based on geographic clustering
    confidence_score: float

    def __post_init__(self):
        self.total_parcels = len(self.parcels)


@dataclass
class ManifestGenerationResult:
    """Result of manifest generation process"""

    manifests: List[OptimizedManifest]
    total_parcels_assigned: int
    unassigned_parcels: List[ManifestParcel]
    total_drivers_used: int
    average_workload: float
    average_route_efficiency: float
    generation_time_seconds: float
    confidence_score: float
    optimization_notes: List[str]


class ManifestService:
    """Domain service for manifest-related business logic"""

    # Constants
    MAX_PARCELS_PER_DRIVER = 20
    TARGET_UTILIZATION = 0.85  # Target 85% capacity utilization
    MAX_ROUTE_DURATION_HOURS = 8
    MIN_PARCELS_FOR_CLUSTERING = 3

    @classmethod
    def prioritize_parcels(cls, parcels: List[ManifestParcel]) -> List[ManifestParcel]:
        """
        Prioritize parcels by urgency and value

        Args:
            parcels: List of parcels to prioritize

        Returns:
            Sorted list of parcels (highest priority first)
        """

        def priority_score(parcel: ManifestParcel) -> float:
            score = 0.0

            # Urgency (highest weight)
            if parcel.delivery_priority == 1:  # Urgent
                score += 100.0
            elif parcel.delivery_priority == 2:  # Standard
                score += 50.0
            else:  # Economy
                score += 10.0

            # Value (medium weight)
            if parcel.value_dollars > 500:
                score += 30.0
            elif parcel.value_dollars > 100:
                score += 15.0

            # Signature requirement (low weight)
            if parcel.requires_signature:
                score += 10.0

            return score

        return sorted(parcels, key=priority_score, reverse=True)

    @classmethod
    def cluster_parcels_by_postcode(cls, parcels: List[ManifestParcel]) -> Dict[str, List[ManifestParcel]]:
        """
        Group parcels by postcode for geographic clustering

        Args:
            parcels: List of parcels to cluster

        Returns:
            Dictionary mapping postcode to list of parcels
        """
        clusters: Dict[str, List[ManifestParcel]] = {}

        for parcel in parcels:
            postcode = parcel.postcode
            if postcode not in clusters:
                clusters[postcode] = []
            clusters[postcode].append(parcel)

        return clusters

    @classmethod
    def assign_parcels_to_drivers(
        cls, parcels: List[ManifestParcel], drivers: List[Driver]
    ) -> Dict[str, List[ManifestParcel]]:
        """
        Assign parcels to drivers based on capacity and load balancing

        Args:
            parcels: Prioritized list of parcels
            drivers: Available drivers

        Returns:
            Dictionary mapping driver_id to assigned parcels
        """
        assignments: Dict[str, List[ManifestParcel]] = {d.driver_id: [] for d in drivers}

        # Sort drivers by remaining capacity (highest first)
        available_drivers = sorted(drivers, key=lambda d: d.remaining_capacity, reverse=True)

        for parcel in parcels:
            # Find driver with most remaining capacity
            for driver in available_drivers:
                if driver.remaining_capacity > 0:
                    assignments[driver.driver_id].append(parcel)
                    driver.current_load += 1
                    break

        return assignments

    @classmethod
    def calculate_workload_score(cls, assigned_parcels: int, max_capacity: int) -> float:
        """
        Calculate workload utilization score

        Args:
            assigned_parcels: Number of parcels assigned
            max_capacity: Maximum driver capacity

        Returns:
            Workload score 0.0-1.0
        """
        if max_capacity == 0:
            return 0.0

        utilization = assigned_parcels / max_capacity
        return min(utilization, 1.0)

    @classmethod
    def calculate_route_efficiency(cls, parcels: List[ManifestParcel]) -> float:
        """
        Calculate route efficiency based on geographic clustering

        Higher score means better clustering (fewer unique postcodes)

        Args:
            parcels: List of parcels in route

        Returns:
            Efficiency score 0.0-1.0
        """
        if not parcels:
            return 0.0

        # Count unique postcodes
        unique_postcodes = len(set(p.postcode for p in parcels))
        total_parcels = len(parcels)

        # Perfect clustering: all parcels in same postcode = 1.0
        # Poor clustering: all different postcodes = closer to 0
        if total_parcels == 0:
            return 0.0

        clustering_ratio = 1 - ((unique_postcodes - 1) / total_parcels)
        return max(0.0, min(clustering_ratio, 1.0))

    @classmethod
    def calculate_overall_confidence(
        cls, manifests: List[OptimizedManifest], total_parcels: int, total_drivers: int
    ) -> float:
        """
        Calculate overall confidence score for manifest generation

        Args:
            manifests: Generated manifests
            total_parcels: Total parcels to assign
            total_drivers: Available drivers

        Returns:
            Confidence score 0.0-1.0
        """
        if not manifests:
            return 0.0

        # Factor 1: Assignment completion rate
        assigned_parcels = sum(m.total_parcels for m in manifests)
        completion_rate = assigned_parcels / total_parcels if total_parcels > 0 else 0.0

        # Factor 2: Average workload balance
        avg_workload = sum(m.workload_score for m in manifests) / len(manifests)

        # Factor 3: Average route efficiency
        avg_efficiency = sum(m.route_efficiency_score for m in manifests) / len(manifests)

        # Factor 4: Driver utilization
        driver_utilization = len(manifests) / total_drivers if total_drivers > 0 else 0.0

        # Weighted combination
        confidence = (
            completion_rate * 0.35 + avg_workload * 0.25 + avg_efficiency * 0.25 + driver_utilization * 0.15
        )

        return min(confidence, 1.0)

    @classmethod
    def estimate_route_metrics(cls, parcel_count: int, dc_location: str) -> Tuple[float, int]:
        """
        Estimate route distance and duration based on parcel count

        Simple heuristic for estimation when maps service unavailable

        Args:
            parcel_count: Number of parcels in route
            dc_location: Distribution center location

        Returns:
            Tuple of (estimated_distance_km, estimated_duration_min)
        """
        # Average assumptions:
        # - 4km between stops
        # - 15 minutes per delivery (including travel)
        # - 10km from DC to first stop

        avg_distance_per_stop_km = 4.0
        avg_time_per_stop_min = 15
        dc_to_first_stop_km = 10.0

        estimated_distance = dc_to_first_stop_km + (parcel_count * avg_distance_per_stop_km)
        estimated_duration = parcel_count * avg_time_per_stop_min

        return (estimated_distance, estimated_duration)

    @classmethod
    def format_route_string(cls, addresses: List[str], max_length: int = 80) -> str:
        """
        Format route addresses for display

        Args:
            addresses: List of addresses in route
            max_length: Maximum display length

        Returns:
            Formatted route string
        """
        route = " → ".join(addresses)
        if len(route) > max_length:
            return route[:max_length] + "..."
        return route

    @classmethod
    def validate_manifest_assignment(cls, manifest: OptimizedManifest) -> Tuple[bool, List[str]]:
        """
        Validate a manifest assignment for errors

        Args:
            manifest: Manifest to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not manifest.driver_id:
            errors.append("Manifest must have a driver assigned")

        if manifest.total_parcels == 0:
            errors.append("Manifest must have at least one parcel")

        if manifest.total_parcels > cls.MAX_PARCELS_PER_DRIVER:
            errors.append(
                f"Manifest exceeds maximum capacity ({manifest.total_parcels} > {cls.MAX_PARCELS_PER_DRIVER})"
            )

        if manifest.estimated_duration_min > (cls.MAX_ROUTE_DURATION_HOURS * 60):
            errors.append(f"Route duration exceeds maximum allowed ({cls.MAX_ROUTE_DURATION_HOURS} hours)")

        if manifest.workload_score < 0.3:
            errors.append("Manifest has low utilization (< 30%) - consider consolidating routes")

        return (len(errors) == 0, errors)
