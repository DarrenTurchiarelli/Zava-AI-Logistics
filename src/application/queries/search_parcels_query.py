"""
Search Parcels Query - CQRS Read Operation
"""
from typing import Dict, Any, List, Optional

from src.infrastructure.database.repositories import ParcelRepository


class SearchParcelsQuery:
    """Query to search parcels by various criteria"""
    
    def __init__(self, parcel_repo: ParcelRepository):
        self.parcel_repo = parcel_repo
    
    async def execute(
        self,
        status: Optional[str] = None,
        recipient_name: Optional[str] = None,
        postcode: Optional[str] = None,
        driver_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search parcels with flexible criteria
        
        Args:
            status: Filter by status
            recipient_name: Filter by recipient name (partial match)
            postcode: Filter by destination postcode
            driver_id: Filter by assigned driver
            limit: Maximum results to return
            
        Returns:
            List of matching parcels
        """
        # Use repository search methods
        if recipient_name:
            return await self.parcel_repo.search_by_recipient(recipient_name, limit)
        elif driver_id:
            return await self.parcel_repo.get_by_driver(driver_id)
        elif postcode:
            return await self.parcel_repo.get_by_postcode(postcode)
        elif status:
            return await self.parcel_repo.get_by_status(status)
        else:
            return await self.parcel_repo.get_all(limit)
    
    async def search_advanced(
        self,
        query: str,
        search_fields: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Advanced search across multiple fields
        
        Args:
            query: Search query string
            search_fields: Fields to search (default: all text fields)
            
        Returns:
            List of matching parcels
        """
        if not search_fields:
            search_fields = ['tracking_number', 'recipient_name', 'sender_name', 'recipient_address']
        
        # Perform search (implementation depends on repository capabilities)
        return await self.parcel_repo.advanced_search(query, search_fields)
