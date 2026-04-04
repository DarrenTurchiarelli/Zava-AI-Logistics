"""
Zava - Fraud Service
Domain Service: Handles fraud detection and risk assessment logic

Extracted from agents/fraud.py module.
Provides centralized business logic for fraud operations.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ThreatLevel(str, Enum):
    """Threat level classifications"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudCategory(str, Enum):
    """Types of fraud detected"""

    PAYMENT_SCAM = "payment_scam"
    PHISHING = "phishing"
    IMPERSONATION = "impersonation"
    DELIVERY_FEE_SCAM = "delivery_fee_scam"
    CREDENTIAL_THEFT = "credential_theft"
    SOCIAL_ENGINEERING = "social_engineering"
    PARCEL_FRAUD = "parcel_fraud"
    UNKNOWN = "unknown"


@dataclass
class ThreatAnalysis:
    """Results of threat analysis"""

    threat_level: ThreatLevel
    fraud_category: FraudCategory
    confidence_score: float  # 0.0 - 1.0
    risk_score: int  # 0 - 100
    risk_indicators: List[str]
    recommended_actions: List[str]
    educational_content: Dict[str, Any]
    alert_security_team: bool
    related_patterns: List[str]
    ai_response: str = ""


class FraudService:
    """Domain service for fraud detection and risk assessment"""

    # Risk score thresholds
    CRITICAL_RISK_THRESHOLD = 90
    HIGH_RISK_THRESHOLD = 70
    MEDIUM_RISK_THRESHOLD = 40
    LOW_RISK_THRESHOLD = 10

    # Fraud patterns (regex patterns for detection)
    FRAUD_PATTERNS = {
        "payment_request": [
            r"pay.*fee",
            r"click.*link.*pay",
            r"urgent.*payment",
            r"customs.*charge",
            r"delivery.*fee.*required",
        ],
        "phishing_link": [r"http[s]?://[^\s]+", r"bit\.ly", r"tinyurl\.com", r"click.*here"],
        "impersonation": [
            r"zava.*support",
            r"customer.*service",
            r"verify.*account",
            r"confirm.*identity",
            r"update.*details",
        ],
        "urgency": [r"urgent", r"immediate", r"act now", r"expire", r"24 hours", r"limited time"],
        "suspicious_domain": [
            r"@[a-z0-9\-]+\.(xyz|top|tk|ml|ga|cf|pw)",  # Suspicious TLDs
            r"zav[a4]",  # Typosquatting
            r"z[a4]v[a4]",
        ],
    }

    @classmethod
    def analyze_message_for_fraud(cls, message_content: str, sender_email: Optional[str] = None) -> ThreatAnalysis:
        """
        Analyze a message for fraud indicators (local/fallback analysis)

        Args:
            message_content: Message text to analyze
            sender_email: Sender's email address (optional)

        Returns:
            ThreatAnalysis object
        """
        risk_indicators = []
        risk_score = 0
        fraud_category = FraudCategory.UNKNOWN

        message_lower = message_content.lower()

        # Check for payment scam patterns
        payment_matches = sum(
            1 for pattern in cls.FRAUD_PATTERNS["payment_request"] if re.search(pattern, message_lower)
        )
        if payment_matches > 0:
            risk_score += payment_matches * 25
            risk_indicators.append(f"Payment request language detected ({payment_matches} patterns)")
            fraud_category = FraudCategory.PAYMENT_SCAM

        # Check for phishing links
        link_matches = sum(1 for pattern in cls.FRAUD_PATTERNS["phishing_link"] if re.search(pattern, message_lower))
        if link_matches > 0:
            risk_score += link_matches * 15
            risk_indicators.append(f"Suspicious links found ({link_matches})")
            if fraud_category == FraudCategory.UNKNOWN:
                fraud_category = FraudCategory.PHISHING

        # Check for impersonation attempts
        impersonation_matches = sum(
            1 for pattern in cls.FRAUD_PATTERNS["impersonation"] if re.search(pattern, message_lower)
        )
        if impersonation_matches > 0:
            risk_score += impersonation_matches * 20
            risk_indicators.append(f"Company impersonation detected ({impersonation_matches} patterns)")
            if fraud_category == FraudCategory.UNKNOWN:
                fraud_category = FraudCategory.IMPERSONATION

        # Check for urgency tactics
        urgency_matches = sum(1 for pattern in cls.FRAUD_PATTERNS["urgency"] if re.search(pattern, message_lower))
        if urgency_matches > 0:
            risk_score += urgency_matches * 10
            risk_indicators.append(f"Urgency pressure tactics ({urgency_matches})")

        # Check sender email if provided
        if sender_email:
            domain_matches = sum(
                1 for pattern in cls.FRAUD_PATTERNS["suspicious_domain"] if re.search(pattern, sender_email.lower())
            )
            if domain_matches > 0:
                risk_score += domain_matches * 30
                risk_indicators.append(f"Suspicious sender domain detected")
                if fraud_category == FraudCategory.UNKNOWN:
                    fraud_category = FraudCategory.PHISHING

        # Cap risk score at 100
        risk_score = min(risk_score, 100)

        # Determine threat level
        threat_level = cls.get_threat_level_from_score(risk_score)

        # Determine confidence
        confidence_score = min(len(risk_indicators) * 0.2, 0.9)  # More indicators = higher confidence

        # Generate recommendations
        recommended_actions = cls.get_recommended_actions(fraud_category, threat_level)

        # Get educational content
        educational_content = cls.get_educational_content(fraud_category)

        # Determine if security team should be alerted
        alert_security = risk_score >= cls.HIGH_RISK_THRESHOLD

        return ThreatAnalysis(
            threat_level=threat_level,
            fraud_category=fraud_category,
            confidence_score=confidence_score,
            risk_score=risk_score,
            risk_indicators=risk_indicators,
            recommended_actions=recommended_actions,
            educational_content=educational_content,
            alert_security_team=alert_security,
            related_patterns=[fraud_category.value] if fraud_category != FraudCategory.UNKNOWN else [],
        )

    @classmethod
    def get_threat_level_from_score(cls, risk_score: int) -> ThreatLevel:
        """
        Determine threat level from risk score

        Args:
            risk_score: Risk score (0-100)

        Returns:
            ThreatLevel enum value
        """
        if risk_score >= cls.CRITICAL_RISK_THRESHOLD:
            return ThreatLevel.CRITICAL
        elif risk_score >= cls.HIGH_RISK_THRESHOLD:
            return ThreatLevel.HIGH
        elif risk_score >= cls.MEDIUM_RISK_THRESHOLD:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW

    @classmethod
    def get_recommended_actions(cls, fraud_category: FraudCategory, threat_level: ThreatLevel) -> List[str]:
        """
        Get recommended actions based on fraud category and threat level

        Args:
            fraud_category: Type of fraud detected
            threat_level: Severity level

        Returns:
            List of recommended actions
        """
        actions = []

        # Category-specific actions
        if fraud_category == FraudCategory.PAYMENT_SCAM:
            actions.append("Do not make any payments")
            actions.append("Block sender immediately")
            actions.append("Report to fraud@zava.com")

        elif fraud_category == FraudCategory.PHISHING:
            actions.append("Do not click any links")
            actions.append("Do not enter personal information")
            actions.append("Verify sender through official channels")

        elif fraud_category == FraudCategory.IMPERSONATION:
            actions.append("Verify sender identity through official Zava channels")
            actions.append("Do not respond to unauthorized requests")
            actions.append("Report impersonation attempt")

        # Threat-level specific actions
        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
            actions.append("Contact Zava security team immediately")
            actions.append("Preserve all evidence (emails, messages, screenshots)")

        if threat_level == ThreatLevel.CRITICAL:
            actions.append("Consider changing passwords if credentials were shared")
            actions.append("Contact your bank if payment information was provided")

        # General actions
        actions.append("Share this warning with others")
        actions.append("Block and delete the message")

        return actions

    @classmethod
    def get_educational_content(cls, fraud_category: FraudCategory) -> Dict[str, Any]:
        """
        Get educational content for a fraud category

        Args:
            fraud_category: Type of fraud

        Returns:
            Dictionary with educational information
        """
        templates = {
            FraudCategory.PAYMENT_SCAM: {
                "title": "🚨 Payment Scam Detected",
                "warning": "This appears to be a fraudulent payment request!",
                "tips": [
                    "Zava never requests payment via text or email",
                    "All legitimate fees are collected at delivery or through official channels",
                    "Scammers often create fake urgency to pressure quick action",
                    "Always verify requests through official Zava customer service",
                ],
            },
            FraudCategory.DELIVERY_FEE_SCAM: {
                "title": "📦 Fake Delivery Fee Scam",
                "warning": "This is a common delivery fee scam!",
                "tips": [
                    "Delivery fees are clearly communicated when you book with Zava",
                    "We never surprise customers with unexpected fees via text/email",
                    "Legitimate delivery issues are handled through proper customer service",
                    "Scammers exploit package anxiety to steal money quickly",
                ],
            },
            FraudCategory.PHISHING: {
                "title": "🎣 Phishing Attempt Detected",
                "warning": "This message is trying to steal your personal information!",
                "tips": [
                    "Check the sender's domain carefully - scammers use similar-looking addresses",
                    "Zava will never ask for passwords or personal details via message",
                    "Hover over links to see the real destination before clicking",
                    "When in doubt, contact us directly through official channels",
                ],
            },
            FraudCategory.IMPERSONATION: {
                "title": "👤 Impersonation Attempt",
                "warning": "Someone is pretending to be Zava!",
                "tips": [
                    "Verify all communications through official Zava contact methods",
                    "Check email addresses and domains carefully",
                    "Official Zava emails come from @zava.com domain only",
                    "Report impersonation attempts to help protect others",
                ],
            },
        }

        return templates.get(
            fraud_category,
            {
                "title": "⚠️ Suspicious Activity Detected",
                "warning": "This message shows signs of potential fraud",
                "tips": [
                    "Be skeptical of unexpected messages requesting action",
                    "Verify requests through official channels",
                    "Trust your instincts - if something feels wrong, it probably is",
                    "Zava will never ask for sensitive information via message",
                ],
            },
        )

    @classmethod
    def calculate_parcel_fraud_risk(
        cls,
        declared_value: Optional[float] = None,
        service_type: Optional[str] = None,
        weight_kg: Optional[float] = None,
        sender_verified: bool = True,
        recipient_verified: bool = True,
        address_complete: bool = True,
    ) -> Tuple[int, List[str]]:
        """
        Calculate fraud risk score for a parcel

        Args:
            declared_value: Parcel value in AUD
            service_type: Type of service (express, standard, etc.)
            weight_kg: Parcel weight
            sender_verified: Whether sender is verified
            recipient_verified: Whether recipient is verified
            address_complete: Whether address information is complete

        Returns:
            Tuple of (risk_score, risk_indicators)
        """
        risk_score = 0
        indicators = []

        # High value increases risk
        if declared_value:
            if declared_value > 1000:
                risk_score += 30
                indicators.append("High value parcel (> $1000)")
            elif declared_value > 500:
                risk_score += 15
                indicators.append("Moderate value parcel (> $500)")

        # Express service can indicate fraud attempts
        if service_type and "express" in service_type.lower():
            risk_score += 10
            indicators.append("Express service selected")

        # Weight anomalies
        if weight_kg is not None:
            if weight_kg < 0.1:
                risk_score += 20
                indicators.append("Suspiciously light package (< 0.1kg)")
            elif weight_kg > 25:
                risk_score += 15
                indicators.append("Very heavy package (> 25kg)")

        # Verification status
        if not sender_verified:
            risk_score += 25
            indicators.append("Sender not verified")

        if not recipient_verified:
            risk_score += 20
            indicators.append("Recipient not verified")

        if not address_complete:
            risk_score += 15
            indicators.append("Incomplete address information")

        # Cap at 100
        risk_score = min(risk_score, 100)

        return (risk_score, indicators)

    @classmethod
    def format_threat_summary(cls, analysis: ThreatAnalysis) -> str:
        """
        Format threat analysis for display

        Args:
            analysis: ThreatAnalysis object

        Returns:
            Formatted summary string
        """
        summary = f"""
Fraud Analysis Summary
================================
Threat Level: {analysis.threat_level.value.upper()}
Fraud Category: {analysis.fraud_category.value}
Risk Score: {analysis.risk_score}/100
Confidence: {analysis.confidence_score * 100:.1f}%

Risk Indicators:
"""
        for indicator in analysis.risk_indicators:
            summary += f"  • {indicator}\n"

        summary += "\nRecommended Actions:\n"
        for action in analysis.recommended_actions:
            summary += f"  ✓ {action}\n"

        if analysis.alert_security_team:
            summary += "\n⚠️ SECURITY TEAM ALERTED\n"

        return summary
