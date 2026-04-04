"""
Get Parcel Query - CQRS Read Operation
"""
from typing import Dict, Any, Optional

from src.infrastructure.database.repositories import ParcelRepository


class GetParcelQuery:
    """Query to get parcel information"""
    
    def __init__(self, parcel_repo: ParcelRepository):
        self.parcel_repo = parcel_repo
    
    async def execute(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """
        Execute parcel lookup by tracking number
        
        Args:
            tracking_number: Tracking number to lookup
            
        Returns:
            Parcel data or None if not found
        """
        return await self.parcel_repo.get_by_tracking_number(tracking_number)
    
    async def get_with_events(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """
        Get parcel with full tracking history
        
        Args:
            tracking_number: Tracking number to lookup
            
        Returns:
            Parcel data with events or None if not found
        """
        parcel = await self.parcel_repo.get_by_tracking_number(tracking_number)
        if not parcel:
            return None
        
        # Get tracking events
        events = await self.parcel_repo.get_tracking_events(tracking_number)
        
        return {
            **parcel,
            'tracking_events': events,
        }
