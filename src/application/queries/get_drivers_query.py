"""
Get Drivers Query - CQRS Read Operation
"""
from typing import Dict, Any, List, Optional


class GetDriversQuery:
    """Query to get driver information"""
    
    def __init__(self, db_client):
        self.db = db_client
    
    async def execute(self, driver_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get drivers
        
        Args:
            driver_id: Optional driver ID to filter
            
        Returns:
            List of drivers
        """
        container = self.db.database.get_container_client('users')
        
        if driver_id:
            query = "SELECT * FROM c WHERE c.role = 'driver' AND c.driver_id = @driver_id"
            parameters = [{'name': '@driver_id', 'value': driver_id}]
        else:
            query = "SELECT * FROM c WHERE c.role = 'driver'"
            parameters = []
        
        drivers = []
        async for driver in container.query_items(query=query, parameters=parameters):
            drivers.append(driver)
        
        return drivers
    
    async def get_available_drivers(self) -> List[Dict[str, Any]]:
        """
        Get drivers available for new assignments
        
        Returns:
            List of available drivers
        """
        # This could check manifests, driver schedules, etc.
        return await self.execute()
