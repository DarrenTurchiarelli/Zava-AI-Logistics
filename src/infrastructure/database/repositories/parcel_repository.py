"""
Parcel Repository

Repository for Parcel domain entities with Cosmos DB implementation.
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from src.domain.models.parcel import Parcel, ParcelStatus
from src.domain.exceptions import EntityNotFoundError, DuplicateEntityError
from .base_repository import IQueryableRepository


class IParcelRepository(IQueryableRepository[Parcel], ABC):
    """
    Parcel repository interface
    
    Defines parcel-specific query operations beyond basic CRUD.
    """
    
    @abstractmethod
    async def get_by_tracking_number(self, tracking_number: str) -> Optional[Parcel]:
        """Get parcel by tracking number"""
        pass
    
    @abstractmethod
    async def get_by_barcode(self, barcode: str) -> Optional[Parcel]:
        """Get parcel by barcode"""
        pass
    
    @abstractmethod
    async def find_by_recipient(
        self,
        name: Optional[str] = None,
        postcode: Optional[str] = None,
        address: Optional[str] = None
    ) -> List[Parcel]:
        """Find parcels by recipient information"""
        pass
    
    @abstractmethod
    async def find_by_driver(self, driver_id: str) -> List[Parcel]:
        """Get all parcels assigned to a driver"""
        pass
    
    @abstractmethod
    async def find_by_status(self, status: ParcelStatus) -> List[Parcel]:
        """Get parcels with specific status"""
        pass
    
    @abstractmethod
    async def find_by_location(self, location: str) -> List[Parcel]:
        """Get parcels at a specific location"""
        pass
    
    @abstractmethod
    async def find_high_risk(self, min_risk_score: int = 70) -> List[Parcel]:
        """Get parcels with high fraud risk scores"""
        pass
    
    @abstractmethod
    async def find_pending_approval(self) -> List[Parcel]:
        """Get parcels requiring approval"""
        pass


class CosmosParcelRepository(IParcelRepository):
    """
    Cosmos DB implementation of Parcel repository
    
    Handles all Cosmos DB-specific operations for parcels.
    """
    
    def __init__(self, database_client):
        """
        Initialize repository with Cosmos DB client
        
        Args:
            database_client: Cosmos database client
        """
        self.database = database_client
        self.container_name = "parcels"
        self._container = None
    
    async def _get_container(self):
        """Get container client (lazy initialization)"""
        if self._container is None:
            self._container = self.database.get_container_client(self.container_name)
        return self._container
    
    async def get_by_id(self, id: str) -> Optional[Parcel]:
        """Get parcel by ID"""
        try:
            container = await self._get_container()
            item = await container.read_item(item=id, partition_key=id)
            return Parcel.from_dict(item)
        except Exception:
            return None
    
    async def get_by_tracking_number(self, tracking_number: str) -> Optional[Parcel]:
        """Get parcel by tracking number"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.tracking_number = @tracking_number"
        parameters = [{"name": "@tracking_number", "value": tracking_number}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters):
            items.append(Parcel.from_dict(item))
        
        return items[0] if items else None
    
    async def get_by_barcode(self, barcode: str) -> Optional[Parcel]:
        """Get parcel by barcode"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.barcode = @barcode"
        parameters = [{"name": "@barcode", "value": barcode}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters):
            items.append(Parcel.from_dict(item))
        
        return items[0] if items else None
    
    async def get_all(self, limit: Optional[int] = None, skip: int = 0) -> List[Parcel]:
        """Get all parcels with pagination"""
        container = await self._get_container()
        query = "SELECT * FROM c ORDER BY c.registration_timestamp DESC"
        
        if limit:
            query += f" OFFSET {skip} LIMIT {limit}"
        
        parcels = []
        async for item in container.query_items(query=query):
            parcels.append(Parcel.from_dict(item))
        
        return parcels
    
    async def create(self, parcel: Parcel) -> Parcel:
        """Create a new parcel"""
        # Check for duplicates
        existing = await self.get_by_barcode(parcel.barcode)
        if existing:
            raise DuplicateEntityError("Parcel", parcel.barcode)
        
        container = await self._get_container()
        item = parcel.to_dict()
        created_item = await container.create_item(body=item)
        return Parcel.from_dict(created_item)
    
    async def update(self, parcel: Parcel) -> Parcel:
        """Update existing parcel"""
        existing = await self.get_by_id(parcel.id)
        if not existing:
            raise EntityNotFoundError("Parcel", parcel.id)
        
        container = await self._get_container()
        item = parcel.to_dict()
        updated_item = await container.replace_item(item=parcel.id, body=item)
        return Parcel.from_dict(updated_item)
    
    async def delete(self, id: str) -> bool:
        """Delete parcel"""
        try:
            container = await self._get_container()
            await container.delete_item(item=id, partition_key=id)
            return True
        except Exception:
            return False
    
    async def exists(self, id: str) -> bool:
        """Check if parcel exists"""
        return await self.get_by_id(id) is not None
    
    async def find_by_criteria(self, criteria: Dict) -> List[Parcel]:
        """Find parcels matching criteria"""
        container = await self._get_container()
        
        # Build query from criteria
        conditions = []
        parameters = []
        
        for i, (key, value) in enumerate(criteria.items()):
            param_name = f"@param{i}"
            conditions.append(f"c.{key} = {param_name}")
            parameters.append({"name": param_name, "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        parcels = []
        async for item in container.query_items(query=query, parameters=parameters):
            parcels.append(Parcel.from_dict(item))
        
        return parcels
    
    async def count(self, criteria: Optional[Dict] = None) -> int:
        """Count parcels"""
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
    
    async def find_by_recipient(
        self,
        name: Optional[str] = None,
        postcode: Optional[str] = None,
        address: Optional[str] = None
    ) -> List[Parcel]:
        """Find parcels by recipient information"""
        container = await self._get_container()
        
        conditions = []
        parameters = []
        
        if name:
            conditions.append("CONTAINS(LOWER(c.recipient_name), @name)")
            parameters.append({"name": "@name", "value": name.lower()})
        
        if postcode:
            conditions.append("c.destination_postcode = @postcode")
            parameters.append({"name": "@postcode", "value": postcode})
        
        if address:
            conditions.append("CONTAINS(LOWER(c.recipient_address), @address)")
            parameters.append({"name": "@address", "value": address.lower()})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        parcels = []
        async for item in container.query_items(query=query, parameters=parameters):
            parcels.append(Parcel.from_dict(item))
        
        return parcels
    
    async def find_by_driver(self, driver_id: str) -> List[Parcel]:
        """Get all parcels assigned to a driver"""
        return await self.find_by_criteria({"assigned_driver_id": driver_id})
    
    async def find_by_status(self, status: ParcelStatus) -> List[Parcel]:
        """Get parcels with specific status"""
        return await self.find_by_criteria({"current_status": status.value})
    
    async def find_by_location(self, location: str) -> List[Parcel]:
        """Get parcels at a specific location"""
        return await self.find_by_criteria({"current_location": location})
    
    async def find_high_risk(self, min_risk_score: int = 70) -> List[Parcel]:
        """Get parcels with high fraud risk scores"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.fraud_risk_score >= @min_score"
        parameters = [{"name": "@min_score", "value": min_risk_score}]
        
        parcels = []
        async for item in container.query_items(query=query, parameters=parameters):
            parcels.append(Parcel.from_dict(item))
        
        return parcels
    
    async def find_pending_approval(self) -> List[Parcel]:
        """Get parcels requiring approval"""
        return await self.find_by_criteria({"requires_approval": True, "approval_status": "pending"})
