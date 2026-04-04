"""
Approve Request Command - CQRS Write Operation
"""
from typing import Dict, Any, Optional
from datetime import datetime

from src.infrastructure.database.repositories import ApprovalRepository


class ApproveRequestCommand:
    """Command to approve or deny an approval request"""
    
    def __init__(self, approval_repo: ApprovalRepository):
        self.approval_repo = approval_repo
    
    async def execute(
        self,
        approval_id: str,
        decision: str,  # 'approved' or 'denied'
        reviewer_username: str,
        reviewer_notes: str = '',
        ai_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute approval decision
        
        Args:
            approval_id: Approval request ID
            decision: Decision (approved/denied)
            reviewer_username: Username of reviewer
            reviewer_notes: Reviewer's notes
            ai_reasoning: Optional AI agent reasoning
            
        Returns:
            Updated approval request
        """
        # Update approval request
        updated = await self.approval_repo.update_status(
            approval_id=approval_id,
            decision=decision,
            reviewer_username=reviewer_username,
            reviewer_notes=reviewer_notes,
            ai_reasoning=ai_reasoning,
            reviewed_at=datetime.now().isoformat(),
        )
        
        return {
            'success': True,
            'approval_id': approval_id,
            'decision': decision,
            'approval': updated,
        }
