"""
Fraud Detection → Customer Service Workflow
Intelligent agent chain for proactive fraud prevention and customer protection

Workflow:
1. Fraud Agent detects suspicious activity (high risk score > 0.7)
2. → Customer Service Agent generates personalized warning message
3. → Notification sent to customer with fraud prevention tips
4. → If customer confirms fraud, Identity Agent verifies legitimacy
5. → System automatically flags and holds suspicious parcels
"""

import asyncio
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.base import customer_service_agent, identity_agent

# Import agents
from agents.fraud import analyze_with_fraud_agent, fraud_risk_agent


@dataclass
class FraudWorkflowContext:
    """Context object passed through the workflow"""

    workflow_id: str
    initiated_at: str
    trigger_type: str  # 'message_report', 'pattern_detection', 'manual_review'

    # Fraud detection data
    message_content: Optional[str] = None
    sender_info: Optional[Dict[str, Any]] = None
    suspicious_parcel_ids: Optional[List[str]] = None

    # Fraud analysis results
    fraud_risk_score: Optional[float] = None
    fraud_indicators: Optional[List[str]] = None
    recommended_action: Optional[str] = None

    # Customer service data
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None

    # Generated outputs
    customer_warning_message: Optional[str] = None
    notification_sent: bool = False
    notification_method: Optional[str] = None

    # Identity verification (if needed)
    identity_verification_required: bool = False
    identity_verified: bool = False
    verification_details: Optional[Dict[str, Any]] = None

    # Final outcome
    parcels_held: List[str] = None
    case_escalated: bool = False
    escalation_reason: Optional[str] = None
    workflow_status: str = "in_progress"  # in_progress, completed, failed
    completion_time: Optional[str] = None

    def __post_init__(self):
        if self.parcels_held is None:
            self.parcels_held = []


class FraudToCustomerServiceWorkflow:
    """Manages fraud detection to customer service agent workflow"""

    def __init__(self):
        self.workflow_log = []

    async def execute(
        self,
        message_content: str,
        sender_info: Dict[str, Any],
        customer_info: Dict[str, Any],
        trigger_type: str = "message_report",
    ) -> FraudWorkflowContext:
        """
        Execute fraud detection → customer service workflow

        Args:
            message_content: Suspicious message text
            sender_info: Information about the sender
            customer_info: Customer contact information
            trigger_type: How this workflow was triggered

        Returns:
            FraudWorkflowContext with complete workflow results
        """

        # Initialize workflow context
        context = FraudWorkflowContext(
            workflow_id=f"FRAUD-WF-{uuid.uuid4().hex[:8].upper()}",
            initiated_at=datetime.now(timezone.utc).isoformat(),
            trigger_type=trigger_type,
            message_content=message_content,
            sender_info=sender_info,
            customer_name=customer_info.get("name"),
            customer_email=customer_info.get("email"),
            customer_phone=customer_info.get("phone"),
        )

        self._log_step(context, "Workflow initiated", "info")

        try:
            # Step 1: Fraud Detection Analysis
            await self._step_1_fraud_detection(context)

            # Step 2: Determine if customer notification needed
            if context.fraud_risk_score >= 0.7:  # High risk threshold
                await self._step_2_generate_customer_warning(context)

                # Step 3: Send notification
                await self._step_3_send_notification(context)

                # Step 4: Check if identity verification needed
                if context.fraud_risk_score >= 0.85:  # Very high risk
                    context.identity_verification_required = True
                    await self._step_4_identity_verification(context)

                # Step 5: Hold parcels if fraud confirmed
                if context.fraud_risk_score >= 0.9 or context.identity_verification_required:
                    await self._step_5_hold_parcels(context)

            # Mark workflow as completed
            context.workflow_status = "completed"
            context.completion_time = datetime.now(timezone.utc).isoformat()
            self._log_step(context, "Workflow completed successfully", "success")

        except Exception as e:
            context.workflow_status = "failed"
            context.completion_time = datetime.now(timezone.utc).isoformat()
            self._log_step(context, f"Workflow failed: {str(e)}", "error")
            raise

        return context

    async def _step_1_fraud_detection(self, context: FraudWorkflowContext):
        """Step 1: Analyze message with fraud detection agent"""
        self._log_step(context, "Starting fraud detection analysis", "info")

        # Call fraud detection agent
        fraud_analysis = await analyze_with_fraud_agent(
            message_content=context.message_content, sender_info=context.sender_info
        )

        # Extract results
        context.fraud_risk_score = fraud_analysis.get("risk_score", 0.0)
        context.fraud_indicators = fraud_analysis.get("risk_indicators", [])
        context.recommended_action = fraud_analysis.get("recommended_action", "monitor")

        if fraud_analysis.get("associated_tracking_numbers"):
            context.suspicious_parcel_ids = fraud_analysis["associated_tracking_numbers"]

        self._log_step(
            context,
            f"Fraud analysis complete: Risk Score = {context.fraud_risk_score:.2f}, Action = {context.recommended_action}",
            "info",
        )

    async def _step_2_generate_customer_warning(self, context: FraudWorkflowContext):
        """Step 2: Generate personalized customer warning via Customer Service Agent"""
        self._log_step(context, "Generating customer warning message", "info")

        # Build context for customer service agent
        customer_service_context = {
            "customer_name": context.customer_name,
            "fraud_risk_score": context.fraud_risk_score,
            "fraud_indicators": context.fraud_indicators,
            "suspicious_parcels": context.suspicious_parcel_ids or [],
            "sender_details": context.sender_info,
            "request_type": "fraud_warning",
        }

        # Create prompt for customer service agent
        prompt = f"""
Generate a personalized fraud warning message for customer: {context.customer_name}

FRAUD DETECTION ALERT:
- Risk Score: {context.fraud_risk_score:.0%} (HIGH RISK)
- Detected Indicators: {', '.join(context.fraud_indicators[:3])}
- Recommended Action: {context.recommended_action}

Context:
- Suspicious message received claiming to be from Zava
- Sender: {context.sender_info.get('sender', 'Unknown')}
- Message Type: {context.sender_info.get('message_type', 'email')}

Generate a professional, clear warning message that:
1. Alerts the customer to potential fraud
2. Explains what we detected
3. Provides fraud prevention tips
4. Offers legitimate contact methods
5. Requests confirmation if they initiated contact
6. Uses reassuring, protective tone (not alarming)

Keep message concise (200-300 words), professional, and actionable.
"""

        # Call customer service agent
        cs_response = await customer_service_agent(
            {"customer_name": context.customer_name, "inquiry": prompt, "context": customer_service_context}
        )

        # Extract generated message
        if cs_response.get("success"):
            context.customer_warning_message = cs_response.get("response", "")
            self._log_step(context, "Customer warning message generated", "success")
        else:
            # Fallback to template if agent fails
            context.customer_warning_message = self._generate_fallback_warning(context)
            self._log_step(context, "Using fallback warning template", "warning")

    async def _step_3_send_notification(self, context: FraudWorkflowContext):
        """Step 3: Send notification to customer"""
        self._log_step(context, "Sending fraud warning notification", "info")

        # Determine best notification method based on risk level
        if context.fraud_risk_score >= 0.9:
            # Very high risk: multi-channel notification
            notification_methods = ["email", "sms", "phone_call"]
            context.notification_method = "multi_channel"
        elif context.fraud_risk_score >= 0.8:
            # High risk: email + SMS
            notification_methods = ["email", "sms"]
            context.notification_method = "email_sms"
        else:
            # Medium-high risk: email only
            notification_methods = ["email"]
            context.notification_method = "email"

        # Simulate sending notification
        # In production, this would integrate with actual notification services
        notification_result = await self._send_customer_notification(
            context.customer_email, context.customer_phone, context.customer_warning_message, notification_methods
        )

        context.notification_sent = notification_result["success"]

        if context.notification_sent:
            self._log_step(context, f"Notification sent via {context.notification_method}", "success")
        else:
            self._log_step(context, "Notification failed to send", "error")

    async def _step_4_identity_verification(self, context: FraudWorkflowContext):
        """Step 4: Request identity verification for very high risk cases"""
        self._log_step(context, "Initiating identity verification", "info")

        # Build verification request
        verification_request = {
            "customer_name": context.customer_name,
            "verification_type": "fraud_prevention",
            "risk_level": "critical" if context.fraud_risk_score >= 0.9 else "high",
            "context": {
                "workflow_id": context.workflow_id,
                "fraud_score": context.fraud_risk_score,
                "suspicious_parcels": context.suspicious_parcel_ids,
            },
        }

        # Call identity verification agent
        identity_response = await identity_agent(verification_request)

        if identity_response.get("success"):
            context.identity_verified = identity_response.get("verified", False)
            context.verification_details = {
                "method": identity_response.get("verification_method"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": identity_response.get("confidence_score", 0.0),
            }

            status = "verified" if context.identity_verified else "failed"
            self._log_step(context, f"Identity verification {status}", "info")
        else:
            self._log_step(context, "Identity verification unavailable", "warning")

    async def _step_5_hold_parcels(self, context: FraudWorkflowContext):
        """Step 5: Hold suspicious parcels pending review"""
        self._log_step(context, "Holding suspicious parcels", "info")

        if context.suspicious_parcel_ids:
            # Simulate parcel hold
            # In production, this would update parcel status in database
            context.parcels_held = context.suspicious_parcel_ids.copy()
            context.case_escalated = True
            context.escalation_reason = (
                f"Fraud risk score: {context.fraud_risk_score:.0%}, Identity verification required"
            )

            self._log_step(context, f"Held {len(context.parcels_held)} parcels for security review", "warning")
        else:
            self._log_step(context, "No specific parcels identified to hold", "info")

    async def _send_customer_notification(
        self, email: Optional[str], phone: Optional[str], message: str, methods: List[str]
    ) -> Dict[str, Any]:
        """Simulate sending notification to customer"""
        # In production, integrate with:
        # - SendGrid/AWS SES for email
        # - Twilio/AWS SNS for SMS
        # - Voice API for phone calls

        print(f"\n{'='*70}")
        print("📧 FRAUD WARNING NOTIFICATION")
        print(f"{'='*70}")
        print(f"To: {email or 'N/A'}")
        print(f"Phone: {phone or 'N/A'}")
        print(f"Methods: {', '.join(methods)}")
        print(f"\n{message}")
        print(f"{'='*70}\n")

        return {"success": True, "methods_used": methods, "timestamp": datetime.now(timezone.utc).isoformat()}

    def _generate_fallback_warning(self, context: FraudWorkflowContext) -> str:
        """Generate fallback warning message if AI agent fails"""
        return f"""
Dear {context.customer_name},

🛡️ IMPORTANT SECURITY ALERT

We've detected a suspicious message claiming to be from Zava that may be attempting to defraud you.

WHAT WE DETECTED:
• Risk Level: HIGH ({context.fraud_risk_score:.0%})
• Suspicious indicators: {', '.join(context.fraud_indicators[:3])}

PLEASE BE AWARE:
• We NEVER request payment updates via unsolicited messages
• We NEVER ask for personal information through email/SMS
• Always verify communications through our official channels

IMMEDIATE ACTIONS:
1. DO NOT click any links in the suspicious message
2. DO NOT provide any personal or payment information
3. Report the message to: security@dtlogistics.com.au
4. Contact us directly at 1300 384 669 to verify

If you did NOT initiate recent contact with us, please reply immediately.

Your security is our priority.

Zava Security Team
Phone: 1300 384 669
Email: security@dtlogistics.com.au
"""

    def _log_step(self, context: FraudWorkflowContext, message: str, level: str):
        """Log workflow step for audit trail"""
        log_entry = {
            "workflow_id": context.workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "level": level,
        }
        self.workflow_log.append(log_entry)

        # Print to console for visibility
        emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "•")

        print(f"{emoji} [{context.workflow_id}] {message}")

    def get_workflow_summary(self, context: FraudWorkflowContext) -> Dict[str, Any]:
        """Generate workflow summary for reporting"""
        return {
            "workflow_id": context.workflow_id,
            "status": context.workflow_status,
            "initiated_at": context.initiated_at,
            "completed_at": context.completion_time,
            "fraud_detection": {
                "risk_score": context.fraud_risk_score,
                "indicators": context.fraud_indicators,
                "action": context.recommended_action,
            },
            "customer_engagement": {
                "notification_sent": context.notification_sent,
                "notification_method": context.notification_method,
                "identity_verified": context.identity_verified,
            },
            "outcome": {
                "parcels_held": len(context.parcels_held),
                "parcel_ids": context.parcels_held,
                "case_escalated": context.case_escalated,
                "escalation_reason": context.escalation_reason,
            },
            "workflow_log": self.workflow_log,
        }


# Convenience function for easy import
async def fraud_detection_to_customer_service_workflow(
    message_content: str,
    sender_info: Dict[str, Any],
    customer_info: Dict[str, Any],
    trigger_type: str = "message_report",
) -> Dict[str, Any]:
    """
    Execute fraud detection → customer service workflow

    Args:
        message_content: Suspicious message text
        sender_info: Information about the sender (sender, message_type, etc.)
        customer_info: Customer contact info (name, email, phone)
        trigger_type: How workflow was triggered

    Returns:
        Workflow summary with complete results
    """
    workflow = FraudToCustomerServiceWorkflow()
    context = await workflow.execute(
        message_content=message_content, sender_info=sender_info, customer_info=customer_info, trigger_type=trigger_type
    )

    return workflow.get_workflow_summary(context)


# Example usage
async def example_usage():
    """Example of how to use the fraud workflow"""

    # Simulate a suspicious message report
    result = await fraud_detection_to_customer_service_workflow(
        message_content="""
        URGENT: Your Zava parcel delivery failed!
        Click here to reschedule: http://fake-dt-logistics.com/reschedule
        Pay $5 redelivery fee: [SUSPICIOUS LINK]
        Reply with card details to confirm.
        """,
        sender_info={
            "sender": "no-reply@fake-dt-logistics.com",
            "message_type": "email",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        customer_info={"name": "Sarah Johnson", "email": "sarah.j@example.com", "phone": "+61412345678"},
        trigger_type="customer_report",
    )

    print("\n" + "=" * 70)
    print("WORKFLOW SUMMARY")
    print("=" * 70)
    print(f"Status: {result['status']}")
    print(f"Fraud Risk: {result['fraud_detection']['risk_score']:.0%}")
    print(f"Notification Sent: {result['customer_engagement']['notification_sent']}")
    print(f"Parcels Held: {result['outcome']['parcels_held']}")
    print(f"Case Escalated: {result['outcome']['case_escalated']}")
    print("=" * 70)


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
