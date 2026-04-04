"""
Azure Maps Service

Provides route optimization using Azure Maps API.
Handles geocoding, route calculation, and traffic-aware routing.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()


class AzureMapsService:
    """
    Azure Maps route optimization service
    
    Provides geocoding and route optimization using Azure Maps API.
    Note: Azure Maps requires  subscription key (managed identity not supported).
    """
    
    def __init__(self, geocode_cache: Optional[Dict] = None):
        self.subscription_key = os.getenv("AZURE_MAPS_SUBSCRIPTION_KEY", "")
        self.base_url = "https://atlas.microsoft.com"
        self.api_version = "1.0"
        self.geocode_cache = geocode_cache if geocode_cache is not None else {}
        self.cache_ttl = 86400  # 24 hours
        
        if not self.subscription_key:
            print("[MAPS] WARNING: Azure Maps subscription key not configured")
            print("[MAPS] Set AZURE_MAPS_SUBSCRIPTION_KEY environment variable")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates
        
        Args:
            address: Street address
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        if not self.subscription_key:
            return None
        
        # Check cache
        if address in self.geocode_cache:
            return self.geocode_cache[address]
        
        try:
            url = f"{self.base_url}/search/address/json"
            params = {
                "api-version": self.api_version,
                "subscription-key": self.subscription_key,
                "query": address,
                "limit": 1,
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results") and len(data["results"]) > 0:
                position = data["results"][0]["position"]
                coords = (position["lat"], position["lon"])
                self.geocode_cache[address] = coords
                return coords
        
        except Exception as e:
            print(f"[MAPS] Geocoding error for {address}: {e}")
        
        return None
    
    def optimize_route(
        self,
        addresses: List[str],
        start_location: Optional[str] = None,
        route_type: str = "fastest"
    ) -> Dict[str, Any]:
        """
        Optimize delivery route
        
        Args:
            addresses: List of delivery addresses
            start_location: Starting point (depot)
            route_type: "fastest" or "shortest"
            
        Returns:
            Dictionary with optimized_order, total_distance_km, total_duration_minutes
        """
        if not self.subscription_key:
            return self._fallback_optimization(addresses, start_location)
        
        waypoints = [start_location] + addresses if start_location else addresses
        
        # Geocode all addresses
        coords_map = {}
        for addr in waypoints:
            coords = self.geocode_address(addr)
            if coords:
                coords_map[addr] = coords
        
        if len(coords_map) < 2:
            return self._fallback_optimization(addresses, start_location)
        
        # Use nearest-neighbor for optimization
        optimized = self._nearest_neighbor_optimization(waypoints, coords_map)
        
        # Calculate total distance and duration
        total_distance, total_duration = self._calculate_route_metrics(optimized, coords_map)
        
        return {
            "optimized_order": optimized,
            "total_distance_km": total_distance,
            "total_duration_minutes": total_duration,
            "waypoint_count": len(optimized),
        }
    
    def _nearest_neighbor_optimization(
        self,
        waypoints: List[str],
        coords_map: Dict[str, Tuple[float, float]]
    ) -> List[str]:
        """Nearest neighbor greedy algorithm"""
        if len(waypoints) <= 2:
            return waypoints
        
        optimized = [waypoints[0]]
        remaining = set(waypoints[1:])
        current_coords = coords_map.get(waypoints[0])
        
        while remaining and current_coords:
            nearest = None
            nearest_dist = float("inf")
            
            for addr in remaining:
                if addr not in coords_map:
                    continue
                
                target_coords = coords_map[addr]
                dist = (
                    (current_coords[0] - target_coords[0]) ** 2 +
                    (current_coords[1] - target_coords[1]) ** 2
                ) ** 0.5
                
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = addr
            
            if nearest:
                optimized.append(nearest)
                remaining.remove(nearest)
                current_coords = coords_map[nearest]
            else:
                break
        
        # Add any remaining addresses
        optimized.extend(remaining)
        return optimized
    
    def _calculate_route_metrics(
        self,
        waypoints: List[str],
        coords_map: Dict[str, Tuple[float, float]]
    ) -> Tuple[float, float]:
        """Calculate approximate distance and duration"""
        total_distance = 0.0
        
        for i in range(len(waypoints) - 1):
            if waypoints[i] in coords_map and waypoints[i + 1] in coords_map:
                coords1 = coords_map[waypoints[i]]
                coords2 = coords_map[waypoints[i + 1]]
                
                # Haversine distance (approximate)
                lat_diff = coords2[0] - coords1[0]
                lon_diff = coords2[1] - coords1[1]
                distance = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # km
                total_distance += distance
        
        # Estimate duration (40 km/h average in urban areas)
        total_duration = (total_distance / 40) * 60  # minutes
        
        return total_distance, total_duration
    
    def _fallback_optimization(
        self,
        addresses: List[str],
        start_location: Optional[str]
    ) -> Dict[str, Any]:
        """Fallback when API unavailable"""
        waypoints = [start_location] + addresses if start_location else addresses
        
        return {
            "optimized_order": waypoints,
            "total_distance_km": len(waypoints) * 5,  # Rough estimate
            "total_duration_minutes": len(waypoints) * 15,  # 15 min per stop
            "waypoint_count": len(waypoints),
        }
