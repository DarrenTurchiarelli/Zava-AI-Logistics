"""
Create Manifest Command - CQRS Write Operation
"""
from typing import Dict, Any, List
from datetime import datetime
import uuid

from src.infrastructure.database.repositories import ManifestRepository


class CreateManifestCommand:
    """Command to create a new driver manifest"""
    
    def __init__(self, manifest_repo: ManifestRepository):
        self.manifest_repo = manifest_repo
    
    async def execute(
        self,
        driver_id: str,
        driver_name: str,
        parcels: List[Dict[str, Any]],
        manifest_date: str,
        depot_location: str = '',
    ) -> Dict[str, Any]:
        """
        Execute manifest creation
        
        Args:
            driver_id: Driver identifier
            driver_name: Driver full name
            parcels: List of parcel dictionaries
            manifest_date: Manifest date (YYYY-MM-DD)
            depot_location: Depot location
            
        Returns:
            Created manifest data
        """
        # Generate manifest ID
        manifest_id = f"MAN{uuid.uuid4().hex[:8].upper()}"
        
        # Create manifest
        manifest = await self.manifest_repo.create(
            manifest_id=manifest_id,
            driver_id=driver_id,
            driver_name=driver_name,
            parcels=parcels,
            manifest_date=manifest_date,
            depot_location=depot_location,
            status='pending',
        )
        
        return {
            'success': True,
            'manifest_id': manifest_id,
            'manifest': manifest,
        }
