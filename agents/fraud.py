#!/usr/bin/env python3
"""
Fraud & Risk Agent Integration

Integrates with Azure AI services for fraud detection:
1. Azure AI Foundry Agent (asst_ARutauXhW2tWVWB0UVqALhFA) - Primary analysis
2. Fallback local analysis - Pattern matching when AI unavailable

Note: Microsoft Security Copilot is an embedded experience in Azure services
(Microsoft Defender, Sentinel, Purview) accessed through Azure portal, not via API.
For programmatic fraud detection, this module uses Azure AI Foundry agents.

Provides comprehensive fraud detection, threat assessment, and security recommendations.
"""

import re
import uuid
import asyncio
import os
import socket
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from azure.identity import AzureCliCredential, ManagedIdentityCredential
from azure.ai.projects import AIProjectClient
from dotenv import load_dotenv

load_dotenv()
# Configuration - Using centralized agent ID from .env
FRAUD_RISK_AGENT_ID = os.getenv("FRAUD_RISK_AGENT_ID", "asst_ARutauXhW2tWVWB0UVqALhFA")  # Fallback to old ID
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
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Check if a domain exists using DNS lookup"""
        try:
            # Try to get MX records (email servers) first - most reliable for email domains
            socket.getaddrinfo(domain, None)
            return True
        except socket.gaierror:
            # Domain doesn't resolve
            return False
        except Exception:
            # Network error or other issue - assume valid to avoid false positives
            return True
    
    def _extract_domain_from_email(self, email: str) -> Optional[str]:
        """Extract domain from email address"""
        if "@" not in email:
            return None
        try:
            return email.split("@")[1].strip().lower()
        except:
            return None
    
    async def analyze_suspicious_message(self, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Analyze suspicious message using Azure AI Foundry agent"""
        return await self._analyze_with_azure_ai_foundry(message_content, sender_info)
    
    async def _analyze_with_azure_ai_foundry(self, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Analyze suspicious message using Azure AI Foundry agent"""
        
        try:
            # Run synchronous AI agent call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._analyze_with_ai_sync, message_content, sender_info)
                
        except Exception as e:
            import traceback
            print(f"❌ Azure AI agent error: {type(e).__name__}: {str(e)}")
            print(f"📋 Full traceback:")
            traceback.print_exc()
            print(f"⚠️ Falling back to local analysis")
            # Fallback to basic local analysis
            return self._fallback_analysis(message_content, sender_info)
    
    def _analyze_with_ai_sync(self, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Synchronous Azure AI agent analysis"""
        try:
            # Connect to Azure AI using sync client
            # Use Managed Identity when explicitly enabled (Azure deployment)
            if os.getenv('USE_MANAGED_IDENTITY', 'false').lower() == 'true':
                credential = ManagedIdentityCredential()
            else:
                credential = AzureCliCredential()
            
            project_client = AIProjectClient(
                endpoint=AZURE_AI_PROJECT_ENDPOINT, 
                credential=credential
            )
            
            # Prepare prompt for the Fraud & Risk Agent
            analysis_prompt = f"""
            You are analyzing a message for DT Logistics customers to detect fraud and scams.
            
            CONTEXT: DT Logistics is a delivery/logistics company. Common fraud patterns include:
            - Fake delivery fee scams (demanding payment for nonexistent packages)
            - Phishing emails impersonating DT Logistics
            - Payment scams requesting urgent money transfers
            - Fake tracking links leading to credential theft
            
            NOT FRAUD: Normal business emails, internal communications, legitimate inquiries, 
            automated notifications from real companies (LinkedIn, Microsoft, etc.), and 
            professional correspondence should be marked as LOW risk.

            MESSAGE CONTENT: "{message_content}"
            SENDER INFO: "{sender_info}"

            Analyze carefully and provide:
            1. Risk Level (Low/Medium/High/Critical) - Only use Medium+ if there are clear fraud indicators
            2. Fraud Type (Payment Scam/Phishing/Impersonation/Delivery Fee Scam/Other/None)
            3. Confidence Score (0-100%) - Be conservative, legitimate emails should be <30%
            4. Risk Indicators (list ONLY specific, concrete threats - not generic observations)
            5. Recommended Actions (specific steps for user)
            6. Security Alert Level (Yes/No for escalation) - Only Yes for High/Critical threats
            7. Related Patterns (if this matches known fraud campaigns)

            BE CONSERVATIVE: Err on the side of marking unclear messages as Low risk rather than false positives.
            Format your response clearly with each section labeled.
            """
            
            # Create thread, run agent, and wait for completion
            run_result = project_client.agents.create_thread_and_process_run(
                agent_id=self.agent_id,
                thread={
                    "messages": [
                        {
                            "role": "user",
                            "content": analysis_prompt
                        }
                    ]
                }
            )
            
            # Extract the AI response from the result
            print(f"🔍 Run result status: {run_result.status}")
            print(f"🔍 Run thread_id: {run_result.thread_id}")
            
            # Get the assistant's response from the thread
            ai_response_obj = project_client.agents.messages.get_last_message_text_by_role(
                thread_id=run_result.thread_id,
                role="assistant"
            )
            
            # Extract text from MessageTextContent object
            if ai_response_obj:
                if hasattr(ai_response_obj, 'value'):
                    ai_response = ai_response_obj.value
                elif hasattr(ai_response_obj, 'text'):
                    ai_response = ai_response_obj.text.value if hasattr(ai_response_obj.text, 'value') else str(ai_response_obj.text)
                else:
                    ai_response = str(ai_response_obj)
                print(f"✅ Extracted AI response: {len(ai_response)} chars")
                print(f"📄 AI Response preview: {ai_response[:500]}...")
            else:
                print(f"⚠️ No AI response received")
                ai_response = ""
            
            # Parse the AI response into structured data
            analysis = self._parse_ai_response(ai_response, message_content, sender_info)
            analysis.ai_response = ai_response
            
            print(f"✅ AI analysis complete - using Azure AI Foundry agent")
            return analysis
            
        except Exception as e:
            import traceback
            print(f"❌ Sync AI agent error: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            raise  # Re-raise to be caught by outer async handler
    
    def _parse_ai_response(self, ai_response: str, message_content: str, sender_info: str) -> ThreatAnalysis:
        """Parse the AI agent response into structured ThreatAnalysis"""
        
        print(f"🔍 Parsing AI response ({len(ai_response)} chars)")
        
        # Extract threat level - check for explicit level markers first
        threat_level = ThreatLevel.LOW  # Default to LOW (safer than MEDIUM)
        response_lower = ai_response.lower()
        
        # Look for structured response format: "Risk Level**: Low/Medium/High/Critical"
        risk_level_match = re.search(r'risk level[*:\s]+(\w+)', response_lower)
        if risk_level_match:
            level = risk_level_match.group(1)
            if "critical" in level:
                threat_level = ThreatLevel.CRITICAL
            elif "high" in level:
                threat_level = ThreatLevel.HIGH
            elif "medium" in level:
                threat_level = ThreatLevel.MEDIUM
            elif "low" in level:
                threat_level = ThreatLevel.LOW
        # Fallback to keyword search
        elif "critical" in response_lower:
            threat_level = ThreatLevel.CRITICAL
        elif "high risk" in response_lower or "high threat" in response_lower:
            threat_level = ThreatLevel.HIGH
        elif "medium risk" in response_lower or "medium threat" in response_lower:
            threat_level = ThreatLevel.MEDIUM
        elif "low risk" in response_lower or "low threat" in response_lower:
            threat_level = ThreatLevel.LOW
        
        # Extract fraud category
        fraud_category = FraudCategory.UNKNOWN  # Default
        
        # Check for "Fraud Type**: None" pattern first
        fraud_type_match = re.search(r'fraud type[*:\s]+(\w+)', response_lower)
        if fraud_type_match and "none" in fraud_type_match.group(1):
            fraud_category = FraudCategory.UNKNOWN
        elif "payment scam" in response_lower or "delivery fee" in response_lower or "fee scam" in response_lower:
            fraud_category = FraudCategory.DELIVERY_FEE_SCAM
        elif "phishing" in response_lower:
            fraud_category = FraudCategory.PHISHING
        elif "impersonation" in response_lower or "impersonate" in response_lower:
            fraud_category = FraudCategory.IMPERSONATION
        elif "credential" in response_lower or "password" in response_lower:
            fraud_category = FraudCategory.CREDENTIAL_THEFT
        elif "social engineering" in response_lower:
            fraud_category = FraudCategory.SOCIAL_ENGINEERING
        
        # Extract confidence score from AI response, or calculate based on evidence
        confidence_score = 0.7  # Default
        confidence_match = re.search(r'(\d+)%', ai_response)
        if confidence_match:
            confidence_score = float(confidence_match.group(1)) / 100
        
        # Extract risk indicators (look for bullet points, numbered lists, or key phrases)
        risk_indicators = []
        lines = ai_response.split('\n')
        
        # Check if AI explicitly said "None" or no threats
        if any(phrase in response_lower for phrase in ["none identified", "no risk indicators", "no threats", "appears to be legitimate"]):
            print("✅ AI identified no risk indicators")
            risk_indicators = []
        else:
            # First pass: Look for explicitly marked indicators
            in_indicators_section = False
            for line in lines:
                line_stripped = line.strip()
                
                # Detect indicator sections start
                if any(header in line.lower() for header in ["4. **risk indicator", "risk indicators:"]):
                    in_indicators_section = True
                    continue
                
                # Detect section end (next numbered section like "5. **Recommended")
                if in_indicators_section and re.match(r'^\d+\.\s*\*\*[A-Z]', line_stripped):
                    in_indicators_section = False
                    continue
                
                # Extract indicators only from the indicators section
                if in_indicators_section:
                    if line_stripped.startswith(('•', '-', '*')) and len(line_stripped) > 15:
                        # Clean up the indicator text
                        indicator = re.sub(r'^[•\-*]\s*', '', line_stripped).strip()
                        if indicator and len(indicator) > 10 and "none" not in indicator.lower():
                            risk_indicators.append(indicator)
        
        # Second pass: If no indicators found, extract key phrases
        if len(risk_indicators) < 2:
            # Look for common fraud indicator patterns in the response
            if "payment" in response_lower and "link" in response_lower:
                risk_indicators.append("Requests payment through suspicious link")
            if "urgent" in response_lower or "immediate" in response_lower:
                risk_indicators.append("Uses urgency tactics to pressure quick action")
            if "imperson" in response_lower:
                risk_indicators.append("Attempts to impersonate legitimate organization")
            if "click" in response_lower and ("link" in response_lower or "url" in response_lower):
                risk_indicators.append("Contains suspicious links or URLs")
        
        # Only use fallback if AI response suggests there should be indicators
        # Don't add fake indicators for legitimate emails
        if len(risk_indicators) == 0 and threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            print("⚠️ High/Critical threat but no indicators found, using content analysis")
            risk_indicators = self._extract_indicators_from_content(message_content)
        
        print(f"📋 Extracted {len(risk_indicators)} risk indicators")
        
        # If AI didn't provide confidence score, calculate based on evidence strength
        if not confidence_match:
            print("⚠️ No confidence score from AI, calculating based on evidence")
            has_payment = "payment" in message_content.lower() or "fee" in message_content.lower()
            has_urgency = any(word in message_content.lower() for word in ["urgent", "immediate", "now"])
            has_links = "http" in message_content.lower() or "click" in message_content.lower()
            
            confidence_score = self._calculate_confidence_score(
                risk_indicators=risk_indicators,
                threat_level=threat_level,
                fraud_category=fraud_category,
                has_payment=has_payment,
                has_urgency=has_urgency,
                has_links=has_links
            )
            print(f"📊 Calculated confidence: {confidence_score:.0%}")
        
        # Generate recommendations based on category
        recommended_actions = self._generate_recommendations(fraud_category, threat_level)
        
        # Determine security alert - only for high/critical threats with high confidence
        alert_security = (
            threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] and 
            confidence_score >= 0.95
        )
        
        # Educational content
        educational_content = self._get_educational_content(fraud_category, threat_level)
        
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
        print(f"⚠️ Using fallback analysis for message: {message_content[:100]}...")
        content_lower = message_content.lower()
        
        # Enhanced pattern detection
        risk_indicators = []
        
        # Payment and fee detection - only flag if combined with action requests or links
        payment_keywords = ["pay now", "payment required", "pay fee", "pay immediately", "send money", "transfer funds"]
        suspicious_payment_patterns = [
            r"pay.*(?:now|immediately|urgent|asap|click|link)",
            r"(?:fee|payment|charge).*(?:required|must|click|link|http)",
            r"\$\d+.*(?:now|immediately|click|pay|link)"
        ]
        
        found_payment = False
        for keyword in payment_keywords:
            if keyword in content_lower:
                found_payment = True
                risk_indicators.append(f"Suspicious payment request: '{keyword}'")
                break
        
        if not found_payment:
            for pattern in suspicious_payment_patterns:
                if re.search(pattern, content_lower):
                    found_payment = True
                    risk_indicators.append("Payment request combined with urgency or suspicious links")
                    break
        
        # Urgency detection
        urgency_words = ["urgent", "immediate", "now", "quickly", "asap", "expire", "today", "final"]
        found_urgency = [word for word in urgency_words if word in content_lower]
        if found_urgency:
            risk_indicators.append(f"Urgency language used: {', '.join(found_urgency)}")
        
        # Link detection
        if "http" in content_lower or "www." in content_lower or "click" in content_lower:
            risk_indicators.append("Contains suspicious links or click requests")
        
        # DT Logistics impersonation
        if "dt logistics" in content_lower or "dt log" in content_lower:
            risk_indicators.append("Possible DT Logistics impersonation attempt")
        
        # Account verification scams
        if any(word in content_lower for word in ["verify", "confirm", "update", "suspend", "lock"]):
            risk_indicators.append("Account verification scam indicators")
        
        # Prize/reward scams
        if any(word in content_lower for word in ["won", "winner", "prize", "reward", "claim"]):
            risk_indicators.append("Prize or reward scam indicators")
        
        # Personal info requests
        if any(word in content_lower for word in ["password", "pin", "ssn", "card number", "account number"]):
            risk_indicators.append("Requests sensitive personal information")
        
        # Suspicious sender patterns - flag if sender claims to be DT Logistics but isn't
        if sender_info != "unknown" and "@" in sender_info:
            sender_lower = sender_info.lower()
            domain = self._extract_domain_from_email(sender_info)
            
            # Check if sender claims to be DT Logistics (in message or sender name) but uses wrong domain
            claims_dt_logistics = "dt" in sender_lower or "logistics" in sender_lower or "dt logistics" in content_lower
            is_official_domain = any(official in sender_lower for official in ["dtlogistics.com", "dt-logistics.com"])
            
            if claims_dt_logistics and not is_official_domain:
                risk_indicators.append(f"Sender impersonating DT Logistics from unofficial domain: {sender_info}")
            
            # Validate domain exists - flag typosquatting or fake domains
            if domain and not is_official_domain:
                # Check for common typosquatting patterns
                suspicious_patterns = [
                    r"dt.*log[il1]stics",  # dt-log1stics, dt-logilstics
                    r"dt.*logi[sz]tic",    # dt-logiztic, dt-logistic
                    r"dtlogi[sz]tic",      # dtlogiztics
                ]
                
                for pattern in suspicious_patterns:
                    if re.search(pattern, domain):
                        risk_indicators.append(f"Typosquatting domain detected: {domain}")
                        break
                
                # Validate domain actually exists
                if not self._is_valid_domain(domain):
                    risk_indicators.append(f"Sender using non-existent domain: {domain}")
        
        # Determine threat level based on combination of factors
        threat_score = len(risk_indicators)
        has_multiple_red_flags = threat_score >= 3
        has_payment_and_urgency = found_payment and found_urgency
        has_link_and_payment = ("http" in content_lower or "click" in content_lower) and found_payment
        
        if has_multiple_red_flags or has_payment_and_urgency or has_link_and_payment:
            threat_level = ThreatLevel.HIGH
        elif threat_score >= 2:
            threat_level = ThreatLevel.MEDIUM
        elif threat_score >= 1:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = ThreatLevel.LOW
        
        # Determine fraud category
        if found_payment and ("delivery" in content_lower or "package" in content_lower or "parcel" in content_lower):
            fraud_category = FraudCategory.DELIVERY_FEE_SCAM
        elif found_payment:
            fraud_category = FraudCategory.PAYMENT_SCAM
        elif "http" in content_lower or "click" in content_lower:
            fraud_category = FraudCategory.PHISHING
        elif "verify" in content_lower or "confirm" in content_lower:
            fraud_category = FraudCategory.CREDENTIAL_THEFT
        else:
            fraud_category = FraudCategory.UNKNOWN
        
        if not risk_indicators:
            risk_indicators = ["Message analyzed - no major threats detected"]
        
        # Calculate confidence score based on number and strength of indicators
        confidence_score = self._calculate_confidence_score(
            risk_indicators=risk_indicators,
            threat_level=threat_level,
            fraud_category=fraud_category,
            has_payment=found_payment,
            has_urgency=bool(found_urgency),
            has_links="http" in content_lower or "click" in content_lower
        )
        
        print(f"📊 Fallback analysis: {threat_level.value} threat, {len(risk_indicators)} indicators, {confidence_score:.0%} confidence")
        
        return ThreatAnalysis(
            threat_level=threat_level,
            fraud_category=fraud_category,
            confidence_score=confidence_score,
            risk_indicators=risk_indicators,
            recommended_actions=self._generate_recommendations(fraud_category, threat_level),
            educational_content=self._get_educational_content(fraud_category, threat_level),
            alert_security_team=(threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] and confidence_score >= 0.95),
            related_patterns=[f"Analyzed {len(message_content)} characters", "Fallback analysis - Azure AI unavailable"],
            ai_response="Fallback analysis used - Azure AI agent was unavailable"
        )
    
    def _calculate_confidence_score(
        self, 
        risk_indicators: List[str], 
        threat_level: ThreatLevel,
        fraud_category: FraudCategory,
        has_payment: bool = False,
        has_urgency: bool = False,
        has_links: bool = False
    ) -> float:
        """Calculate confidence score based on strength of evidence"""
        
        # Base score starts at 0.5 (50%)
        score = 0.5
        
        # Number of indicators increases confidence
        indicator_count = len(risk_indicators)
        if indicator_count == 0:
            return 0.3  # Very low confidence - no clear indicators
        elif indicator_count == 1:
            score = 0.5  # Medium-low confidence
        elif indicator_count == 2:
            score = 0.65  # Medium confidence
        elif indicator_count == 3:
            score = 0.75  # Good confidence
        elif indicator_count >= 4:
            score = 0.85  # High confidence
        
        # Strong fraud patterns increase confidence
        if has_payment and has_urgency and has_links:
            score += 0.10  # Classic scam pattern - very confident
        elif (has_payment and has_urgency) or (has_payment and has_links):
            score += 0.05  # Strong pattern
        
        # Specific fraud categories with clear evidence
        if fraud_category in [FraudCategory.DELIVERY_FEE_SCAM, FraudCategory.PAYMENT_SCAM]:
            if has_payment and has_urgency:
                score += 0.05  # Very clear pattern
        
        # High-severity indicators suggest higher confidence
        high_severity_indicators = [
            "typosquatting",
            "non-existent domain",
            "impersonating",
            "sensitive personal information"
        ]
        
        for indicator in risk_indicators:
            indicator_lower = indicator.lower()
            if any(severity in indicator_lower for severity in high_severity_indicators):
                score += 0.05
                break
        
        # Cap at 0.95 for fallback analysis (never 100% without AI confirmation)
        return min(score, 0.95)
    
    def _generate_recommendations(self, fraud_category: FraudCategory, threat_level: ThreatLevel) -> List[str]:
        """Generate specific recommendations based on threat analysis"""
        recommendations = []
        
        # Threat-appropriate base recommendations
        if threat_level == ThreatLevel.LOW:
            recommendations.append("Exercise caution with this message")
            if fraud_category != FraudCategory.UNKNOWN:
                recommendations.append("Verify sender identity through official channels")
        elif threat_level == ThreatLevel.MEDIUM:
            recommendations.append("Do not respond to this message")
            recommendations.append("Verify with DT Logistics through official contact methods")
            recommendations.append("Be cautious of any links or attachments")
        else:  # HIGH or CRITICAL
            recommendations.append("Do not respond to this message")
            recommendations.append("Block the sender immediately")
            recommendations.append("Delete this message")
        
        # Category-specific recommendations
        if fraud_category in [FraudCategory.PAYMENT_SCAM, FraudCategory.DELIVERY_FEE_SCAM]:
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                recommendations.extend([
                    "Do not click any payment links",
                    "Contact DT Logistics customer service directly to verify",
                    "Check your official DT Logistics account for real status"
                ])
            elif threat_level == ThreatLevel.MEDIUM:
                recommendations.append("Verify any payment requests through official DT Logistics channels")
                
        elif fraud_category == FraudCategory.PHISHING:
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                recommendations.extend([
                    "Do not enter personal information anywhere",
                    "Do not click links or download attachments",
                    "Report to anti-phishing authorities"
                ])
            elif threat_level == ThreatLevel.MEDIUM:
                recommendations.append("Do not click suspicious links or provide personal information")
        
        elif fraud_category == FraudCategory.CREDENTIAL_THEFT:
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                recommendations.extend([
                    "Do not provide passwords or login credentials",
                    "Do not click verification links in this message"
                ])
        
        # High/Critical threat additional actions
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            recommendations.extend([
                "Report to authorities if you've lost money or provided information",
                "Warn family and friends about this scam pattern"
            ])
            if "click" in fraud_category.value or fraud_category == FraudCategory.PHISHING:
                recommendations.append("Consider changing passwords if you clicked any links")
        
        # Low threat - minimal actions
        if threat_level == ThreatLevel.LOW and fraud_category == FraudCategory.UNKNOWN:
            recommendations = [
                "Message appears low-risk but verify sender if needed",
                "Contact DT Logistics directly if you have concerns about your delivery"
            ]
        
        return recommendations
    
    def _extract_indicators_from_content(self, message_content: str) -> List[str]:
        """Extract risk indicators directly from message content"""
        indicators = []
        content_lower = message_content.lower()
        
        # Payment indicators
        if any(word in content_lower for word in ["pay", "payment", "fee", "$", "charge"]):
            indicators.append("Contains payment or fee request")
        
        # Urgency indicators
        if any(word in content_lower for word in ["urgent", "immediate", "now", "today", "expire"]):
            indicators.append("Uses urgent or time-pressure language")
        
        # Link indicators
        if "http" in content_lower or "click" in content_lower or "link" in content_lower:
            indicators.append("Contains links or click requests")
        
        # Impersonation indicators
        if "dt logistics" in content_lower or "dt log" in content_lower:
            indicators.append("Claims to be from DT Logistics")
        
        # Account/credential indicators
        if any(word in content_lower for word in ["verify", "confirm", "suspend", "account"]):
            indicators.append("Requests account verification or action")
        
        if not indicators:
            indicators.append("Suspicious message pattern detected")
        
        return indicators
    
    def _get_educational_content(self, fraud_category: FraudCategory, threat_level: ThreatLevel) -> Dict[str, Any]:
        """Get educational content based on fraud category and threat level"""
        
        # For low threat, provide minimal educational content
        if threat_level == ThreatLevel.LOW:
            return {
                "title": "✅ Low Risk Message",
                "warning": "This message appears to be relatively safe, but always stay vigilant",
                "tips": [
                    "The message doesn't show major red flags",
                    "Verify sender identity if you have any doubts",
                    "Be cautious with unexpected requests"
                ],
                "actions": [
                    "Proceed with normal caution",
                    "Verify through official channels if uncertain"
                ]
            }
        
        # For medium to critical threats, use category-specific templates
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