#!/usr/bin/env python3
"""
Fraud & Risk Agent Integration

Integrates with the existing Azure AI Foundry Fraud & Risk Agent (asst_ARutauXhW2tWVWB0UVqALhFA)
for analyzing suspicious messages, detecting fraud patterns, educating users, 
and providing security recommendations for DT Logistics.
"""

import re
import uuid
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from dotenv import load_dotenv

load_dotenv()

# Existing Fraud & Risk Agent ID
FRAUD_RISK_AGENT_ID = "asst_ARutauXhW2tWVWB0UVqALhFA"
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

class ThreatLevel(Enum):
    """Threat level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FraudCategory(Enum):
    """Types of fraud detected"""
    PAYMENT_SCAM = "payment_scam"
    PHISHING = "phishing"
    IMPERSONATION = "impersonation"
    DELIVERY_FEE_SCAM = "delivery_fee_scam"
    CREDENTIAL_THEFT = "credential_theft"
    SOCIAL_ENGINEERING = "social_engineering"
    UNKNOWN = "unknown"

@dataclass
class ThreatAnalysis:
    """Results of threat analysis"""
    threat_level: ThreatLevel
    fraud_category: FraudCategory
    confidence_score: float  # 0.0 - 1.0
    risk_indicators: List[str]
    recommended_actions: List[str]
    educational_content: Dict[str, Any]
    alert_security_team: bool
    related_patterns: List[str]
    ai_response: str = ""  # Full AI agent response

class FraudRiskAgent:
    """Integration with Azure AI Foundry Fraud & Risk Agent"""
    
    def __init__(self):
        self.agent_id = FRAUD_RISK_AGENT_ID
        self.educational_templates = self._load_educational_templates()
        
    def _load_educational_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load educational content templates"""
        return {
            "payment_scam": {
                "title": "🚨 Payment Scam Detected",
                "warning": "This appears to be a fraudulent payment request!",
                "tips": [
                    "DT Logistics never requests payment via text or email",
                    "All legitimate fees are collected at delivery or through official channels",
                    "Scammers often create fake urgency to pressure quick action",
                    "Always verify requests through official DT Logistics customer service"
                ],
                "actions": [
                    "Do not click any links in the message",
                    "Do not provide personal or payment information",
                    "Block the sender immediately",
                    "Report to authorities if you provided any information"
                ]
            },
            "delivery_fee_scam": {
                "title": "📦 Fake Delivery Fee Scam",
                "warning": "This is a common delivery fee scam!",
                "tips": [
                    "Delivery fees are clearly communicated when you book with DT Logistics",
                    "We never surprise customers with unexpected fees via text/email",
                    "Legitimate delivery issues are handled through proper customer service",
                    "Scammers exploit package anxiety to steal money quickly"
                ],
                "actions": [
                    "Check your official DT Logistics account for real delivery status",
                    "Contact customer service directly if you have delivery concerns",
                    "Never pay unexpected fees through links in messages",
                    "Share this warning with family and friends"
                ]
            },
            "phishing": {
                "title": "🎣 Phishing Attempt Detected",
                "warning": "This message is trying to steal your personal information!",
                "tips": [
                    "Check the sender's domain carefully - scammers use similar-looking addresses",
                    "DT Logistics will never ask for passwords or personal details via message",
                    "Hover over links to see the real destination before clicking",
                    "When in doubt, contact us directly through official channels"
                ],
                "actions": [
                    "Do not click any links or download attachments",
                    "Do not enter personal information",
                    "Verify the request through official DT Logistics website",
                    "Report suspicious messages to help protect others"
                ]
            },
            "general": {
                "title": "⚠️ Suspicious Message Detected",
                "warning": "This message shows signs of potential fraud",
                "tips": [
                    "Be skeptical of unexpected messages requesting action",
                    "Verify requests through official channels",
                    "Trust your instincts - if something feels wrong, it probably is",
                    "DT Logistics will never ask for sensitive information via message"
                ],
                "actions": [
                    "Do not respond to the message",
                    "Block the sender",
                    "Contact DT Logistics directly if you have concerns",
                    "Report suspicious messages to help protect others"
                ]
            }
        }
    
    async def analyze_suspicious_message(self, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Analyze suspicious message using Azure AI Foundry agent"""
        
        try:
            # Connect to Azure AI and get analysis from the Fraud & Risk Agent
            async with (
                AzureCliCredential() as credential,
                AIProjectClient(
                    endpoint=AZURE_AI_PROJECT_ENDPOINT, 
                    credential=credential
                ) as project_client,
            ):
                # Create a thread for conversation
                thread = await project_client.agents.create_thread()
                
                # Prepare prompt for the Fraud & Risk Agent
                analysis_prompt = f"""
                Analyze this suspicious message for fraud patterns and security risks:

                MESSAGE CONTENT: "{message_content}"
                SENDER INFO: "{sender_info}"

                Please provide:
                1. Risk Level (Low/Medium/High/Critical)
                2. Fraud Type (Payment Scam/Phishing/Impersonation/Delivery Fee Scam/Other)
                3. Confidence Score (0-100%)
                4. Risk Indicators (list specific threats found)
                5. Recommended Actions (specific steps for user)
                6. Security Alert Level (Yes/No for escalation)
                7. Related Patterns (if this matches known fraud campaigns)

                Format your response clearly with each section labeled.
                """
                
                # Send message to Fraud & Risk Agent
                await project_client.agents.create_message(
                    thread_id=thread.id,
                    role="user", 
                    content=analysis_prompt
                )
                
                # Run the agent and get response
                run = await project_client.agents.create_and_process_run(
                    thread_id=thread.id,
                    assistant_id=self.agent_id
                )
                
                # Get the agent's response
                messages = await project_client.agents.list_messages(thread_id=thread.id)
                ai_response = ""
                for message in messages.data:
                    if message.role == "assistant":
                        for content in message.content:
                            if hasattr(content, 'text'):
                                ai_response = content.text.value
                                break
                        break
                
                # Parse the AI response into structured data
                analysis = self._parse_ai_response(ai_response, message_content, sender_info)
                analysis.ai_response = ai_response
                
                # Clean up
                await project_client.agents.delete_thread(thread.id)
                
                return analysis
                
        except Exception as e:
            print(f"❌ Azure AI agent unavailable ({e}), using fallback analysis")
            # Fallback to basic local analysis
            return self._fallback_analysis(message_content, sender_info)
    
    def _parse_ai_response(self, ai_response: str, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Parse the AI agent response into structured ThreatAnalysis"""
        
        # Extract threat level
        threat_level = ThreatLevel.MEDIUM  # Default
        if "critical" in ai_response.lower():
            threat_level = ThreatLevel.CRITICAL
        elif "high" in ai_response.lower():
            threat_level = ThreatLevel.HIGH
        elif "low" in ai_response.lower():
            threat_level = ThreatLevel.LOW
        
        # Extract fraud category
        fraud_category = FraudCategory.UNKNOWN  # Default
        response_lower = ai_response.lower()
        if "payment scam" in response_lower or "delivery fee" in response_lower:
            fraud_category = FraudCategory.DELIVERY_FEE_SCAM
        elif "phishing" in response_lower:
            fraud_category = FraudCategory.PHISHING
        elif "impersonation" in response_lower:
            fraud_category = FraudCategory.IMPERSONATION
        
        # Extract confidence score
        confidence_score = 0.7  # Default
        confidence_match = re.search(r'(\d+)%', ai_response)
        if confidence_match:
            confidence_score = float(confidence_match.group(1)) / 100
        
        # Extract risk indicators (look for bullet points or numbered lists)
        risk_indicators = []
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')) and len(line) > 10:
                # Clean up the indicator text
                indicator = re.sub(r'^[•\-*\d\.]\s*', '', line).strip()
                if indicator and len(indicator) > 5:
                    risk_indicators.append(indicator)
        
        # Generate recommendations based on category
        recommended_actions = self._generate_recommendations(fraud_category, threat_level)
        
        # Determine security alert
        alert_security = threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] or "alert" in response_lower
        
        # Educational content
        educational_content = self._get_educational_content(fraud_category)
        
        # Related patterns (extract from AI response)
        related_patterns = []
        if "campaign" in response_lower or "pattern" in response_lower:
            related_patterns.append("Part of known fraud campaign")
        if "similar" in response_lower:
            related_patterns.append("Similar reports received")
        
        return ThreatAnalysis(
            threat_level=threat_level,
            fraud_category=fraud_category,
            confidence_score=confidence_score,
            risk_indicators=risk_indicators if risk_indicators else ["AI analysis completed"],
            recommended_actions=recommended_actions,
            educational_content=educational_content,
            alert_security_team=alert_security,
            related_patterns=related_patterns
        )
    
    def _fallback_analysis(self, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Fallback analysis when Azure AI is unavailable"""
        content_lower = message_content.lower()
        
        # Basic pattern detection
        payment_keywords = sum(1 for word in ["pay", "payment", "fee", "charge", "bill"] if word in content_lower)
        urgency_words = sum(1 for word in ["urgent", "immediate", "now", "quickly"] if word in content_lower)
        
        # Determine threat level
        if payment_keywords >= 2 and urgency_words >= 1:
            threat_level = ThreatLevel.HIGH
            fraud_category = FraudCategory.DELIVERY_FEE_SCAM
        elif "http" in content_lower or "click" in content_lower:
            threat_level = ThreatLevel.MEDIUM
            fraud_category = FraudCategory.PHISHING
        else:
            threat_level = ThreatLevel.MEDIUM
            fraud_category = FraudCategory.UNKNOWN
        
        risk_indicators = [
            "Payment request detected" if payment_keywords > 0 else "Suspicious content",
            "Urgency language used" if urgency_words > 0 else "Potentially fraudulent",
            "Requires verification"
        ]
        
        return ThreatAnalysis(
            threat_level=threat_level,
            fraud_category=fraud_category,
            confidence_score=0.6,
            risk_indicators=risk_indicators,
            recommended_actions=self._generate_recommendations(fraud_category, threat_level),
            educational_content=self._get_educational_content(fraud_category),
            alert_security_team=threat_level == ThreatLevel.HIGH,
            related_patterns=["Fallback analysis - Azure AI unavailable"],
            ai_response="Fallback analysis used - Azure AI agent was unavailable"
        )
    
    def _generate_recommendations(self, fraud_category: FraudCategory, threat_level: ThreatLevel) -> List[str]:
        """Generate specific recommendations based on threat analysis"""
        recommendations = []
        
        # Base recommendations
        recommendations.append("Do not respond to this message")
        recommendations.append("Block the sender immediately")
        
        if fraud_category in [FraudCategory.PAYMENT_SCAM, FraudCategory.DELIVERY_FEE_SCAM]:
            recommendations.extend([
                "Do not click any payment links",
                "Contact DT Logistics customer service directly to verify",
                "Check your official DT Logistics account for real status"
            ])
        elif fraud_category == FraudCategory.PHISHING:
            recommendations.extend([
                "Do not enter personal information anywhere",
                "Do not click links or download attachments",
                "Report to anti-phishing authorities"
            ])
        
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            recommendations.extend([
                "Report to authorities if you've lost money",
                "Warn family and friends about this scam",
                "Consider changing passwords if you clicked any links"
            ])
        
        return recommendations
    
    def _get_educational_content(self, fraud_category: FraudCategory) -> Dict[str, Any]:
        """Get educational content based on fraud category"""
        if fraud_category == FraudCategory.DELIVERY_FEE_SCAM:
            return self.educational_templates["delivery_fee_scam"]
        elif fraud_category == FraudCategory.PAYMENT_SCAM:
            return self.educational_templates["payment_scam"]
        elif fraud_category == FraudCategory.PHISHING:
            return self.educational_templates["phishing"]
        else:
            return self.educational_templates["general"]
    
    def format_analysis_report(self, analysis: ThreatAnalysis) -> str:
        """Format analysis results for display"""
        threat_icons = {
            ThreatLevel.LOW: "🟢",
            ThreatLevel.MEDIUM: "🟡", 
            ThreatLevel.HIGH: "🟠",
            ThreatLevel.CRITICAL: "🔴"
        }
        
        report = f"\n🤖 **FRAUD & RISK AGENT ANALYSIS**\n"
        report += f"{threat_icons[analysis.threat_level]} **Threat Level**: {analysis.threat_level.value.upper()}\n"
        report += f"📊 **Confidence**: {analysis.confidence_score:.1%}\n"
        report += f"🏷️ **Category**: {analysis.fraud_category.value.replace('_', ' ').title()}\n"
        
        if analysis.risk_indicators:
            report += f"\n⚠️ **Risk Indicators Detected**:\n"
            for indicator in analysis.risk_indicators[:3]:  # Limit to top 3
                report += f"  • {indicator}\n"
        
        if analysis.alert_security_team:
            report += f"\n🚨 **SECURITY TEAM ALERTED** - High-risk threat detected\n"
        
        if analysis.related_patterns:
            report += f"\n🔍 **Pattern Analysis**: {analysis.related_patterns[0]}\n"
        
        return report
    
    def format_educational_content(self, educational_content: Dict[str, Any]) -> str:
        """Format educational content for user display"""
        content = f"\n{educational_content['title']}\n"
        content += f"⚠️ {educational_content['warning']}\n\n"
        
        content += "💡 **What You Should Know**:\n"
        for tip in educational_content['tips']:
            content += f"  • {tip}\n"
        
        content += "\n🛡️ **Protective Actions**:\n"
        for action in educational_content['actions']:
            content += f"  • {action}\n"
        
        return content

# Global agent instance
fraud_risk_agent = FraudRiskAgent()

async def analyze_with_fraud_agent(message_content: str, sender_info: str) -> ThreatAnalysis:
    """Convenient wrapper for fraud analysis using existing Azure AI agent"""
    return await fraud_risk_agent.analyze_suspicious_message(message_content, sender_info)