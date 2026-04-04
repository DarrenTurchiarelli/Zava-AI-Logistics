"""
Maps Service - Singleton BingMapsRouter

Centralized Azure Maps/Bing Maps routing service with shared geocode cache.
Prevents duplicate router instances and improves geocoding performance.
"""

import threading
from typing import Optional

from services.maps import BingMapsRouter


class MapsService:
    """
    Singleton wrapper for BingMapsRouter with application-wide geocode caching
    
    Usage:
        maps = get_maps_service()
        result = maps.geocode_address_strict(address)
    """
    
    _instance: Optional['MapsService'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Initialize maps router with shared cache"""
        self._router: Optional[BingMapsRouter] = None
        self._geocode_cache = {}
        self._cache_lock = threading.Lock()
    
    @property
    def router(self) -> BingMapsRouter:
        """
        Get or create BingMapsRouter instance
        
        Returns:
            Shared BingMapsRouter instance with geocode cache
        """
        if self._router is None:
            self._router = BingMapsRouter(
                geocode_cache=self._geocode_cache,
                cache_lock=self._cache_lock
            )
        return self._router
    
    def geocode_address_strict(self, address: str):
        """Proxy to router.geocode_address_strict()"""
        return self.router.geocode_address_strict(address)
    
    def optimize_route(self, addresses, start_location, route_type="fastest"):
        """Proxy to router.optimize_route()"""
        return self.router.optimize_route(addresses, start_location, route_type)
    
    def optimize_all_route_types(self, addresses, start_location):
        """Proxy to router.optimize_all_route_types()"""
        return self.router.optimize_all_route_types(addresses, start_location)
    
    def clear_cache(self):
        """Clear geocoding cache (useful for testing or memory management)"""
        with self._cache_lock:
            self._geocode_cache.clear()
    
    def get_cache_stats(self):
        """Get cache statistics for monitoring"""
        with self._cache_lock:
            return {
                "cached_addresses": len(self._geocode_cache),
                "cache_size_kb": sum(len(str(k)) + len(str(v)) for k, v in self._geocode_cache.items()) / 1024
            }


def get_maps_service() -> MapsService:
    """
    Get singleton MapsService instance
    
    Thread-safe singleton pattern ensures only one BingMapsRouter
    instance exists across the entire application.
    
    Returns:
        Singleton MapsService instance
        
    Example:
        maps = get_maps_service()
        result = maps.geocode_address_strict("123 Main St, Sydney NSW 2000")
    """
    if MapsService._instance is None:
        with MapsService._lock:
            # Double-check locking pattern
            if MapsService._instance is None:
                MapsService._instance = MapsService()
    return MapsService._instance
