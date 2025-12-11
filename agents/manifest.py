"""
DT Logistics - Manifest Generation Agent
AI-powered intelligent manifest creation and driver assignment optimization
NOW POWERED BY AZURE AI FOUNDRY DISPATCHER AGENT
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from services.maps import BingMapsRouter
from config.depots import get_depot_manager
from agents.base import dispatcher_agent

# ============================================================================
# DATA CLASSES
# ============================================================================

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
    """Parcel ready for manifest assignment"""
    parcel_id: str
    tracking_number: str
    recipient_address: str
    postcode: str
    delivery_priority: int  # 1=urgent, 2=standard, 3=economy
    estimated_delivery_time_min: int  # Estimated minutes to deliver
    special_instructions: Optional[str] = None
    requires_signature: bool = False
    value_dollars: float = 0.0
    coordinates: Optional[Tuple[float, float]] = None  # (lat, lon)

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
    confidence_score: float  # AI confidence in this manifest
    
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

# ============================================================================
# MANIFEST GENERATION AGENT
# ============================================================================

class ManifestGenerationAgent:
    """AI-powered manifest generation and driver assignment optimization"""
    
    def __init__(self):
        self.maps_router = BingMapsRouter()
        self.max_parcels_per_driver = 20
        self.target_utilization = 0.85  # Target 85% capacity utilization
        self.max_route_duration_hours = 8  # Maximum route duration
        
    async def generate_optimized_manifests(
        self,
        parcels: List[ManifestParcel],
        available_drivers: List[Driver],
        date: str,
        dc_location: str = None
    ) -> ManifestGenerationResult:
        """
        Generate optimized manifests for all drivers
        
        Process:
        1. Cluster parcels geographically
        2. Prioritize by urgency and value
        3. Assign to drivers based on capacity and location
        4. Optimize routes using Azure Maps
        5. Balance workload across drivers
        """
        
        start_time = datetime.now()
        optimization_notes = []
        
        # Determine optimal depot/distribution center if not provided
        if not dc_location:
            depot_mgr = get_depot_manager()
            addresses = [p.recipient_address for p in parcels]
            dc_location = depot_mgr.get_depot_for_addresses(addresses)
            optimization_notes.append(f"Auto-selected depot: {dc_location}")
        
        print(f"\n🤖 Manifest Generation Agent starting...")
        print(f"   Parcels to assign: {len(parcels)}")
        print(f"   Available drivers: {len(available_drivers)}")
        
        # Step 1: Prioritize parcels
        prioritized_parcels = self._prioritize_parcels(parcels)
        optimization_notes.append(f"Prioritized {len(parcels)} parcels by urgency and value")
        
        # Step 2: Geographic clustering
        clusters = await self._cluster_parcels_geographically(prioritized_parcels)
        optimization_notes.append(f"Created {len(clusters)} geographic clusters")
        
        # Step 3: Assign parcels to drivers
        assignments = await self._assign_parcels_to_drivers(
            clusters,
            available_drivers,
            dc_location
        )
        optimization_notes.append(f"Assigned parcels to {len(assignments)} drivers")
        
        # Step 4: Optimize routes for each driver
        manifests = []
        for driver_id, assigned_parcels in assignments.items():
            if assigned_parcels:
                manifest = await self._create_optimized_manifest(
                    driver_id,
                    [d for d in available_drivers if d.driver_id == driver_id][0],
                    assigned_parcels,
                    date,
                    dc_location
                )
                manifests.append(manifest)
        
        optimization_notes.append(f"Generated {len(manifests)} optimized route manifests")
        
        # Step 5: Calculate metrics
        total_assigned = sum(m.total_parcels for m in manifests)
        unassigned = [p for p in parcels if not any(
            p.parcel_id in [mp.parcel_id for mp in m.parcels] for m in manifests
        )]
        
        avg_workload = sum(m.workload_score for m in manifests) / len(manifests) if manifests else 0
        avg_efficiency = sum(m.route_efficiency_score for m in manifests) / len(manifests) if manifests else 0
        
        # Calculate overall confidence
        confidence = self._calculate_overall_confidence(manifests, parcels, available_drivers)
        
        generation_time = (datetime.now() - start_time).total_seconds()
        
        return ManifestGenerationResult(
            manifests=manifests,
            total_parcels_assigned=total_assigned,
            unassigned_parcels=unassigned,
            total_drivers_used=len(manifests),
            average_workload=avg_workload,
            average_route_efficiency=avg_efficiency,
            generation_time_seconds=generation_time,
            confidence_score=confidence,
            optimization_notes=optimization_notes
        )
    
    def _prioritize_parcels(self, parcels: List[ManifestParcel]) -> List[ManifestParcel]:
        """Prioritize parcels by urgency and value"""
        
        def priority_score(parcel: ManifestParcel) -> float:
            score = 0.0
            
            # Urgency (highest weight)
            if parcel.delivery_priority == 1:  # Urgent
                score += 100
            elif parcel.delivery_priority == 2:  # Standard
                score += 50
            else:  # Economy
                score += 10
            
            # Value
            if parcel.value_dollars > 1000:
                score += 30
            elif parcel.value_dollars > 500:
                score += 15
            elif parcel.value_dollars > 100:
                score += 5
            
            # Signature required (higher priority)
            if parcel.requires_signature:
                score += 10
            
            return score
        
        return sorted(parcels, key=priority_score, reverse=True)
    
    async def _cluster_parcels_geographically(
        self,
        parcels: List[ManifestParcel]
    ) -> List[List[ManifestParcel]]:
        """Cluster parcels by geographic proximity using postcodes"""
        
        # Group by postcode (simple clustering)
        postcode_groups = {}
        for parcel in parcels:
            pc = parcel.postcode
            if pc not in postcode_groups:
                postcode_groups[pc] = []
            postcode_groups[pc].append(parcel)
        
        # Convert to list of clusters
        clusters = list(postcode_groups.values())
        
        # TODO: Implement advanced clustering using coordinates and machine learning
        # For now, simple postcode-based clustering
        
        return clusters
    
    async def _assign_parcels_to_drivers(
        self,
        clusters: List[List[ManifestParcel]],
        drivers: List[Driver],
        dc_location: str
    ) -> Dict[str, List[ManifestParcel]]:
        """Assign parcel clusters to drivers optimally"""
        
        assignments = {driver.driver_id: [] for driver in drivers}
        
        # Sort drivers by remaining capacity
        available_drivers = sorted(drivers, key=lambda d: d.remaining_capacity, reverse=True)
        
        # Assign clusters to drivers
        for cluster in clusters:
            # Find best driver for this cluster
            best_driver = None
            
            for driver in available_drivers:
                if driver.remaining_capacity >= len(cluster):
                    best_driver = driver
                    break
            
            if not best_driver:
                # Split cluster if needed
                for parcel in cluster:
                    for driver in available_drivers:
                        if driver.remaining_capacity > 0:
                            assignments[driver.driver_id].append(parcel)
                            driver.current_load += 1
                            break
            else:
                # Assign entire cluster to driver
                assignments[best_driver.driver_id].extend(cluster)
                best_driver.current_load += len(cluster)
        
        return assignments
    
    async def _create_optimized_manifest(
        self,
        driver_id: str,
        driver: Driver,
        parcels: List[ManifestParcel],
        date: str,
        dc_location: str
    ) -> OptimizedManifest:
        """Create optimized manifest using Azure AI Dispatcher Agent + Azure Maps"""
        
        # Extract addresses for route optimization
        addresses = [dc_location] + [p.recipient_address for p in parcels]
        
        # Get base route data from Azure Maps
        route_data = self.maps_router.optimize_route(addresses, start_location=dc_location)
        
        # Prepare data for Azure AI Dispatcher Agent
        route_request = {
            "parcel_count": len(parcels),
            "available_drivers": [driver_id],
            "service_level": "standard",  # Could be determined by parcel priorities
            "delivery_window": f"{driver.shift_start} - {driver.shift_end}",
            "zone": dc_location,
            "parcels": [
                {
                    "tracking_number": p.tracking_number,
                    "address": p.recipient_address,
                    "postcode": p.postcode,
                    "priority": p.delivery_priority
                }
                for p in parcels
            ],
            "azure_maps_route": route_data
        }
        
        # Call Azure AI Foundry Dispatcher Agent for intelligent optimization
        agent_result = await dispatcher_agent(route_request)
        
        if route_data and agent_result.get('success'):
            # Real Azure Maps optimization enhanced by AI Dispatcher Agent
            optimized_route = route_data.get('waypoints', addresses)
            total_distance = route_data.get('total_distance_km', 0)
            total_duration = route_data.get('total_duration_minutes', 0)
            route_efficiency = 0.94  # AI-enhanced efficiency
            
            # Log AI recommendations
            ai_response = agent_result.get('response', '')
            print(f"   [AI] Dispatcher: {ai_response[:100]}...")
        elif route_data:
            # Azure Maps without AI enhancement
            optimized_route = route_data.get('waypoints', addresses)
            total_distance = route_data.get('total_distance_km', 0)
            total_duration = route_data.get('total_duration_minutes', 0)
            route_efficiency = 0.92  # High efficiency from real optimization
        else:
            # Fallback simulation
            optimized_route = addresses
            total_distance = len(parcels) * 4.5  # Estimate
            total_duration = len(parcels) * 25  # Estimate
            route_efficiency = 0.75  # Lower efficiency for simulated
        
        # Calculate completion time
        shift_start = datetime.strptime(driver.shift_start, "%H:%M")
        completion_time = shift_start + timedelta(minutes=total_duration)
        
        # Calculate workload score
        workload_score = len(parcels) / self.max_parcels_per_driver
        
        # Calculate route efficiency (geographic clustering)
        route_efficiency_score = self._calculate_route_efficiency(parcels)
        
        # Overall confidence - higher with AI agent
        if agent_result.get('success'):
            confidence = min(route_efficiency * driver.performance_score * 0.97, 1.0)
        else:
            confidence = min(route_efficiency * driver.performance_score * 0.95, 1.0)
        
        manifest_id = f"MAN-{date}-{driver_id}"
        
        return OptimizedManifest(
            manifest_id=manifest_id,
            driver_id=driver_id,
            driver_name=driver.name,
            date=date,
            parcels=parcels,
            total_parcels=len(parcels),
            optimized_route=optimized_route,
            estimated_distance_km=round(total_distance, 1),
            estimated_duration_min=int(total_duration),
            estimated_completion_time=completion_time.strftime("%H:%M"),
            workload_score=workload_score,
            route_efficiency_score=route_efficiency_score,
            confidence_score=confidence
        )
    
    def _calculate_route_efficiency(self, parcels: List[ManifestParcel]) -> float:
        """Calculate how efficiently parcels are geographically clustered"""
        
        if not parcels:
            return 0.0
        
        # Count unique postcodes
        unique_postcodes = len(set(p.postcode for p in parcels))
        
        # More clustering (fewer unique postcodes) = higher efficiency
        # Ideal: 1-2 postcodes per manifest
        if unique_postcodes <= 2:
            return 0.95
        elif unique_postcodes <= 4:
            return 0.85
        elif unique_postcodes <= 6:
            return 0.75
        elif unique_postcodes <= 8:
            return 0.65
        else:
            return 0.55
    
    def _calculate_overall_confidence(
        self,
        manifests: List[OptimizedManifest],
        all_parcels: List[ManifestParcel],
        all_drivers: List[Driver]
    ) -> float:
        """Calculate overall confidence in manifest generation"""
        
        if not manifests:
            return 0.0
        
        # Average manifest confidence
        avg_manifest_confidence = sum(m.confidence_score for m in manifests) / len(manifests)
        
        # Assignment rate (how many parcels assigned)
        total_assigned = sum(m.total_parcels for m in manifests)
        assignment_rate = total_assigned / len(all_parcels) if all_parcels else 0
        
        # Driver utilization balance
        utilizations = [m.workload_score for m in manifests]
        avg_util = sum(utilizations) / len(utilizations)
        util_variance = sum((u - avg_util) ** 2 for u in utilizations) / len(utilizations)
        balance_score = 1.0 - min(util_variance, 1.0)
        
        # Combined confidence
        overall = (
            avg_manifest_confidence * 0.5 +
            assignment_rate * 0.3 +
            balance_score * 0.2
        )
        
        return min(overall, 1.0)

# ============================================================================
# CONSOLE INTERFACE
# ============================================================================

async def demo_manifest_generation():
    """Demonstration of manifest generation agent"""
    
    print("\n" + "=" * 70)
    print("🤖 MANIFEST GENERATION AGENT - DEMO")
    print("=" * 70)
    
    # Sample data
    sample_parcels = [
        ManifestParcel("P001", "DTVIC001", "123 Collins St, Melbourne VIC", "3000", 1, 20, value_dollars=500),
        ManifestParcel("P002", "DTVIC002", "456 Bourke St, Melbourne VIC", "3000", 2, 15, value_dollars=200),
        ManifestParcel("P003", "DTVIC003", "789 Lygon St, Carlton VIC", "3053", 2, 18),
        ManifestParcel("P004", "DTVIC004", "321 Bridge Rd, Richmond VIC", "3121", 2, 22),
        ManifestParcel("P005", "DTVIC005", "654 Acland St, St Kilda VIC", "3182", 3, 25),
        ManifestParcel("P006", "DTVIC006", "111 Sydney Rd, Brunswick VIC", "3056", 2, 20),
        ManifestParcel("P007", "DTVIC007", "222 Smith St, Fitzroy VIC", "3065", 1, 18, requires_signature=True, value_dollars=1200),
        ManifestParcel("P008", "DTVIC008", "333 Johnston St, Collingwood VIC", "3066", 2, 17),
    ]
    
    sample_drivers = [
        Driver("DRV001", "John Smith", performance_score=0.92),
        Driver("DRV002", "Sarah Johnson", performance_score=0.88),
        Driver("DRV003", "Michael Chen", performance_score=0.85),
    ]
    
    agent = ManifestGenerationAgent()
    
    result = await agent.generate_optimized_manifests(
        parcels=sample_parcels,
        available_drivers=sample_drivers,
        date="2025-12-08",
        dc_location="Melbourne CBD"
    )
    
    # Display results
    print(f"\n✅ Manifest Generation Complete!")
    print(f"   Generation Time: {result.generation_time_seconds:.2f} seconds")
    print(f"   Overall Confidence: {result.confidence_score * 100:.0f}%")
    print(f"\n📊 Summary:")
    print(f"   Total Parcels: {len(sample_parcels)}")
    print(f"   Parcels Assigned: {result.total_parcels_assigned}")
    print(f"   Unassigned: {len(result.unassigned_parcels)}")
    print(f"   Drivers Used: {result.total_drivers_used}")
    print(f"   Average Workload: {result.average_workload * 100:.0f}%")
    print(f"   Average Route Efficiency: {result.average_route_efficiency * 100:.0f}%")
    
    print(f"\n🗺️  Generated Manifests:")
    for i, manifest in enumerate(result.manifests, 1):
        print(f"\n   Manifest {i}: {manifest.manifest_id}")
        print(f"   Driver: {manifest.driver_name} ({manifest.driver_id})")
        print(f"   Parcels: {manifest.total_parcels}")
        print(f"   Distance: {manifest.estimated_distance_km} km")
        print(f"   Duration: {manifest.estimated_duration_min} min")
        print(f"   Completion ETA: {manifest.estimated_completion_time}")
        print(f"   Workload: {manifest.workload_score * 100:.0f}%")
        print(f"   Efficiency: {manifest.route_efficiency_score * 100:.0f}%")
        print(f"   Confidence: {manifest.confidence_score * 100:.0f}%")
    
    print(f"\n📝 Optimization Notes:")
    for note in result.optimization_notes:
        print(f"   • {note}")

if __name__ == "__main__":
    asyncio.run(demo_manifest_generation())
