"""
Approval Repository

Repository for ApprovalRequest domain entities with Cosmos DB implementation.
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from src.domain.models.approval import ApprovalRequest, ApprovalStatus, ApprovalType
from src.domain.exceptions import EntityNotFoundError, DuplicateEntityError
from .base_repository import IQueryableRepository


class IApprovalRepository(IQueryableRepository[ApprovalRequest], ABC):
    """
    Approval repository interface
    """
    
    @abstractmethod
    async def get_by_request_id(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval by request ID"""
        pass
    
    @abstractmethod
    async def find_by_tracking_number(self, tracking_number: str) -> List[ApprovalRequest]:
        """Get approvals for a parcel"""
        pass
    
    @abstractmethod
    async def find_pending(self) -> List[ApprovalRequest]:
        """Get all pending approvals"""
        pass
    
    @abstractmethod
    async def find_by_type(self, request_type: ApprovalType) -> List[ApprovalRequest]:
        """Get approvals by type"""
        pass
    
    @abstractmethod
    async def find_expired(self) -> List[ApprovalRequest]:
        """Get expired pending approvals"""
        pass


class CosmosApprovalRepository(IApprovalRepository):
    """Cosmos DB implementation of Approval repository"""
    
    def __init__(self, database_client):
        self.database = database_client
        self.container_name = "approval_requests"  # Assuming this container
        self._container = None
    
    async def _get_container(self):
        """Get container client (lazy initialization)"""
        if self._container is None:
            self._container = self.database.get_container_client(self.container_name)
        return self._container
    
    async def get_by_id(self, id: str) -> Optional[ApprovalRequest]:
        """Get approval by ID"""
        try:
            container = await self._get_container()
            item = await container.read_item(item=id, partition_key=id)
            return ApprovalRequest.from_dict(item)
        except Exception:
            return None
    
    async def get_by_request_id(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval by request ID"""
        container = await self._get_container()
        query = "SELECT * FROM c WHERE c.request_id = @request_id"
        parameters = [{"name": "@request_id", "value": request_id}]
        
        items = []
        async for item in container.query_items(query=query, parameters=parameters):
            items.append(ApprovalRequest.from_dict(item))
        
        return items[0] if items else None
    
    async def get_all(self, limit: Optional[int] = None, skip: int = 0) -> List[ApprovalRequest]:
        """Get all approvals"""
        container = await self._get_container()
        query = "SELECT * FROM c ORDER BY c.requested_at DESC"
        
        if limit:
            query += f" OFFSET {skip} LIMIT {limit}"
        
        approvals = []
        async for item in container.query_items(query=query):
            approvals.append(ApprovalRequest.from_dict(item))
        
        return approvals
    
    async def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        """Create a new approval request"""
        existing = await self.get_by_request_id(approval.request_id)
        if existing:
            raise DuplicateEntityError("ApprovalRequest", approval.request_id)
        
        container = await self._get_container()
        item = approval.to_dict()
        created_item = await container.create_item(body=item)
        return ApprovalRequest.from_dict(created_item)
    
    async def update(self, approval: ApprovalRequest) -> ApprovalRequest:
        """Update existing approval"""
        existing = await self.get_by_id(approval.id)
        if not existing:
            raise EntityNotFoundError("ApprovalRequest", approval.id)
        
        container = await self._get_container()
        item = approval.to_dict()
        updated_item = await container.replace_item(item=approval.id, body=item)
        return ApprovalRequest.from_dict(updated_item)
    
    async def delete(self, id: str) -> bool:
        """Delete approval"""
        try:
            container = await self._get_container()
            await container.delete_item(item=id, partition_key=id)
            return True
        except Exception:
            return False
    
    async def exists(self, id: str) -> bool:
        """Check if approval exists"""
        return await self.get_by_id(id) is not None
    
    async def find_by_criteria(self, criteria: Dict) -> List[ApprovalRequest]:
        """Find approvals matching criteria"""
        container = await self._get_container()
        
        conditions = []
        parameters = []
        
        for i, (key, value) in enumerate(criteria.items()):
            param_name = f"@param{i}"
            conditions.append(f"c.{key} = {param_name}")
            parameters.append({"name": param_name, "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause}"
        
        approvals = []
        async for item in container.query_items(query=query, parameters=parameters):
            approvals.append(ApprovalRequest.from_dict(item))
        
        return approvals
    
    async def count(self, criteria: Optional[Dict] = None) -> int:
        """Count approvals"""
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
    
    async def find_by_tracking_number(self, tracking_number: str) -> List[ApprovalRequest]:
        """Get approvals for a parcel"""
        return await self.find_by_criteria({"tracking_number": tracking_number})
    
    async def find_pending(self) -> List[ApprovalRequest]:
        """Get all pending approvals"""
        container = await self._get_container()
        query = """
            SELECT * FROM c 
            WHERE c.status = 'pending'
            ORDER BY c.requested_at ASC
        """
        
        approvals = []
        async for item in container.query_items(query=query):
            approval = ApprovalRequest.from_dict(item)
            approval.check_expiry()  # Update status if expired
            approvals.append(approval)
        
        return approvals
    
    async def find_by_type(self, request_type: ApprovalType) -> List[ApprovalRequest]:
        """Get approvals by type"""
        return await self.find_by_criteria({"request_type": request_type.value})
    
    async def find_expired(self) -> List[ApprovalRequest]:
        """Get expired pending approvals"""
        container = await self._get_container()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        query = """
            SELECT * FROM c 
            WHERE c.status = 'pending'
            AND c.expires_at < @now
        """
        parameters = [{"name": "@now", "value": now}]
        
        approvals = []
        async for item in container.query_items(query=query, parameters=parameters):
            approvals.append(ApprovalRequest.from_dict(item))
        
        return approvals
