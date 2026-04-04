"""
Report Fraud Command - CQRS Write Operation
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from src.infrastructure.agents import fraud_risk_agent


class ReportFraudCommand:
    """Command to report and analyze suspicious activity"""
    
    def __init__(self, db_client):
        self.db = db_client
    
    async def execute(
        self,
        message_content: str,
        reporter_name: str,
        reporter_email: str,
        reporter_phone: Optional[str] = None,
        sender_email: Optional[str] = None,
        attachment_data: Optional[str] = None,
        activity_type: str = 'message',
    ) -> Dict[str, Any]:
        """
        Execute fraud report with AI risk analysis
        
        Args:
            message_content: Suspicious message content
            reporter_name: Reporter's name
            reporter_email: Reporter's email
            reporter_phone: Reporter's phone (optional)
            sender_email: Sender's email (optional)
            attachment_data: Attachment data (optional)
            activity_type: Type of activity (message/package/delivery)
            
        Returns:
            Fraud analysis result with risk score
        """
        # Generate report ID
        report_id = f"FRAUD{uuid.uuid4().hex[:8].upper()}"
        
        # Analyze with AI Fraud Detection Agent
        fraud_analysis = await fraud_risk_agent({
            'message_content': message_content,
            'sender_email': sender_email or 'unknown',
            'activity_type': activity_type,
        })
        
        # Extract risk score
        risk_score = fraud_analysis.get('risk_score', 0)
        
        # Store in database
        container = self.db.database.get_container_client('suspicious_messages')
        await container.create_item({
            'id': report_id,
            'message_content': message_content,
            'reporter_name': reporter_name,
            'reporter_email': reporter_email,
            'reporter_phone': reporter_phone,
            'sender_email': sender_email,
            'attachment_data': attachment_data,
            'activity_type': activity_type,
            'risk_score': risk_score,
            'ai_analysis': fraud_analysis,
            'timestamp': datetime.now(datetime.timezone.utc).isoformat(),
            'status': 'under_review',
        })
        
        return {
            'success': True,
            'report_id': report_id,
            'risk_score': risk_score,
            'analysis': fraud_analysis,
        }
