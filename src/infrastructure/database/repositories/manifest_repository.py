"""
Manifest Repository

Repository for Manifest domain entities with Cosmos DB implementation.
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from src.domain.models.manifest import Manifest, ManifestStatus
from src.domain.exceptions import EntityNotFoundError, DuplicateEntityError
from .base_repository import IQueryableRepository


class IManifestRepository(IQueryableRepository[Manifest], ABC):
    """
    Manifest repository interface
    
    Defines manifest-specific query operations.
    """
    
    @abstractmethod
    async def get_by_manifest_id(self, manifest_id: str) -> Optional[Manifest]:
        """Get manifest by business ID"""
        pass
    
    @abstractmethod
    async def find_by_driver(self, driver_id: str) -> List[Manifest]:
        """Get all manifests for a driver"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: ManifestStatus) -> List[Manifest]:
        """Get manifests with specific status"""
        pass
    
    @abstractmethod
    async def find_active_for_driver(self, driver_id: str) -> Optional[Manifest]:
        """Get active manifest for a driver"""
        pass
    
    @abstractmethod
    async def find_by_date_range(self, start_date: str, end_date: str) -> List[Manifest]:
        """Get manifests created in date range"""
        pass


class CosmosManifestRepository(IManifestRepository):
    """
    Cosmos DB implementation of Manifest repository
    """
    
    def __init__(self, database_client):
        self.database = database_client
        self.container_name = "Manifests"
        self._container = None
    
    async def _get_container(self):
        """Get container client (lazy initialization)"""
        if self._container is None:
            self._container = self.database.get_container_client(self.container_name)
        return self._container
    
    async def get_by_id(self, id: str) -> Optional[Manifest]:
        """Get manifest by ID"""
        try:
            container = await self._get_container()
            item = await container.read_item(item=id, partition_key=id)
            return Manifest.from_dict(item)
        except Exception:
            return None
    
    async def get_by_manifest_id(self, manifest_id: str) -> Optional[Manifest]:
        """Get manifest by business ID"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.manifest_id = @manifest_id"
        parameters = [{"name": "@manifest_id", "value": manifest_id}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters):
            items.append(Manifest.from_dict(item))
        
        return items[0] if items else None
    
    async def get_all(self, limit: Optional[int] = None, skip: int = 0) -> List[Manifest]:
        """Get all manifests with pagination"""
        container = await self._get_container()
        query = "SELECT * FROM c ORDER BY c.created_at DESC"
        
        if limit:
            query += f" OFFSET {skip} LIMIT {limit}"
        
        manifests = []
        async for item in container.query_items(query=query):
            manifests.append(Manifest.from_dict(item))
        
        return manifests
    
    async def create(self, manifest: Manifest) -> Manifest:
        """Create a new manifest"""
        existing = await self.get_by_manifest_id(manifest.manifest_id)
        if existing:
            raise DuplicateEntityError("Manifest", manifest.manifest_id)
        
        container = await self._get_container()
        item = manifest.to_dict()
        created_item = await container.create_item(body=item)
        return Manifest.from_dict(created_item)
    
    async def update(self, manifest: Manifest) -> Manifest:
        """Update existing manifest"""
        existing = await self.get_by_id(manifest.id)
        if not existing:
            raise EntityNotFoundError("Manifest", manifest.id)
        
        container = await self._get_container()
        item = manifest.to_dict()
        updated_item = await container.replace_item(item=manifest.id, body=item)
        return Manifest.from_dict(updated_item)
    
    async def delete(self, id: str) -> bool:
        """Delete manifest"""
        try:
            container = await self._get_container()
            await container.delete_item(item=id, partition_key=id)
            return True
        except Exception:
            return False
    
    async def exists(self, id: str) -> bool:
        """Check if manifest exists"""
        return await self.get_by_id(id) is not None
    
    async def find_by_criteria(self, criteria: Dict) -> List[Manifest]:
        """Find manifests matching criteria"""
        container = await self._get_container()
        
        conditions = []
        parameters = []
        
        for i, (key, value) in enumerate(criteria.items()):
            param_name = f"@param{i}"
            conditions.append(f"c.{key} = {param_name}")
            parameters.append({"name": param_name, "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        manifests = []
        async for item in container.query_items(query=query, parameters=parameters):
            manifests.append(Manifest.from_dict(item))
        
        return manifests
    
    async def count(self, criteria: Optional[Dict] = None) -> int:
        """Count manifests"""
        container = await self._get_container()
        
        if criteria:
            conditions = []
            parameters = []
            
            for i, (key, value) in enumerate(criteria.items()):
                param_name = f"@param{i}"
                conditions.append(f"c.{key} = {param_name}")
                parameters.append({"name": param_name, "value": value})
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        else:
            query = "SELECT VALUE COUNT(1) FROM c"
            parameters = []
        
        item_list = [item async for item in container.query_items(query=query, parameters=parameters)]
        return item_list[0] if item_list else 0
    
    async def find_by_driver(self, driver_id: str) -> List[Manifest]:
        """Get all manifests for a driver"""
        return await self.find_by_criteria({"driver_id": driver_id})
    
    async def find_by_status(self, status: ManifestStatus) -> List[Manifest]:
        """Get manifests with specific status"""
        return await self.find_by_criteria({"status": status.value})
    
    async def find_active_for_driver(self, driver_id: str) -> Optional[Manifest]:
        """Get active manifest for a driver"""
        container = await self._get_container()
        query = """
            SELECT * FROM c 
            WHERE c.driver_id = @driver_id 
            AND c.status IN ('active', 'in_progress')
        """
        parameters = [{"name": "@driver_id", "value": driver_id}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters):
            items.append(Manifest.from_dict(item))
        
        return items[0] if items else None
    
    async def find_by_date_range(self, start_date: str, end_date: str) -> List[Manifest]:
        """Get manifests created in date range"""
        container = await self._get_container()
        query = """
            SELECT * FROM c 
            WHERE c.created_at >= @start_date 
            AND c.created_at <= @end_date
            ORDER BY c.created_at DESC
        """
        parameters = [
            {"name": "@start_date", "value": start_date},
            {"name": "@end_date", "value": end_date}
        ]
        
        manifests = []
        async for item in container.query_items(query=query, parameters=parameters):
            manifests.append(Manifest.from_dict(item))
        
        return manifests
