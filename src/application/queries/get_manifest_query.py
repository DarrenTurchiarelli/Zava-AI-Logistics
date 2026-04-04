"""
Get Manifest Query - CQRS Read Operation
"""
from typing import Dict, Any, List, Optional

from src.infrastructure.database.repositories import ManifestRepository


class GetManifestQuery:
    """Query to get manifest information"""
    
    def __init__(self, manifest_repo: ManifestRepository):
        self.manifest_repo = manifest_repo
    
    async def execute(self, manifest_id: str) -> Optional[Dict[str, Any]]:
        """
        Get manifest by ID
        
        Args:
            manifest_id: Manifest ID
            
        Returns:
            Manifest data or None if not found
        """
        return await self.manifest_repo.get_by_id(manifest_id)
    
    async def get_by_driver(self, driver_id: str) -> List[Dict[str, Any]]:
        """
        Get all manifests for a driver
        
        Args:
            driver_id: Driver ID
            
        Returns:
            List of manifests
        """
        return await self.manifest_repo.get_by_driver(driver_id)
    
    async def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all manifests
        
        Args:
            limit: Maximum results
            
        Returns:
            List of manifests
        """
        return await self.manifest_repo.get_all(limit)
