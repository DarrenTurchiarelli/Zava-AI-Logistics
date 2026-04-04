"""
Get Approvals Query - CQRS Read Operation
"""
from typing import Dict, Any, List, Optional

from src.infrastructure.database.repositories import ApprovalRepository


class GetApprovalsQuery:
    """Query to get approval requests"""
    
    def __init__(self, approval_repo: ApprovalRepository):
        self.approval_repo = approval_repo
    
    async def execute(self, approval_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get approval requests
        
        Args:
            approval_id: Optional approval ID to get specific request
            
        Returns:
            List of approval requests (or single item list)
        """
        if approval_id:
            approval = await self.approval_repo.get_by_id(approval_id)
            return [approval] if approval else []
        else:
            return await self.approval_repo.get_all()
    
    async def get_pending(self) -> List[Dict[str, Any]]:
        """
        Get pending approval requests
        
        Returns:
            List of pending approvals
        """
        return await self.approval_repo.get_pending()
    
    async def get_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get approvals by status
        
        Args:
            status: Status filter (pending/approved/denied)
            
        Returns:
            List of matching approvals
        """
        return await self.approval_repo.get_by_status(status)
