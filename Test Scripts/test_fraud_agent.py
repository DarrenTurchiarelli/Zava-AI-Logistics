#!/usr/bin/env python3
"""
Quick test of the Fraud Risk Agent integration
"""

import asyncio
from fraud_risk_agent import analyze_with_fraud_agent, fraud_risk_agent

async def test_fraud_detection():
    """Test the fraud detection system with sample messages"""
    
    print("\n" + "="*70)
    print("🧪 TESTING FRAUD RISK AGENT")
    print("="*70)
    
    # Test Case 1: Delivery fee scam
    print("\n\n📋 TEST CASE 1: Delivery Fee Scam")
    print("-" * 70)
    message1 = "Your parcel delivery failed. Pay $5.99 now at http://fake-link.com/pay or it will be returned"
    sender1 = "+61 400 123 456"
    
    print(f"Message: {message1}")
    print(f"Sender: {sender1}")
    print("\n🔍 Analyzing...")
    
    try:
        analysis1 = await analyze_with_fraud_agent(message1, sender1)
        print(fraud_risk_agent.format_analysis_report(analysis1))
        print(fraud_risk_agent.format_educational_content(analysis1.educational_content))
        
        print(f"\n✅ Test 1 Complete - Threat Level: {analysis1.threat_level.value.upper()}")
        print(f"   Confidence: {analysis1.confidence_score:.0%}")
        print(f"   Category: {analysis1.fraud_category.value}")
    except Exception as e:
        print(f"\n❌ Test 1 Failed: {e}")
    
    # Test Case 2: Phishing attempt
    print("\n\n📋 TEST CASE 2: Phishing Attempt")
    print("-" * 70)
    message2 = "DT Logistics: Update your account information immediately to avoid suspension. Click here: http://dt-logistics-verify.com"
    sender2 = "no-reply@dtlogistics-info.com"
    
    print(f"Message: {message2}")
    print(f"Sender: {sender2}")
    print("\n🔍 Analyzing...")
    
    try:
        analysis2 = await analyze_with_fraud_agent(message2, sender2)
        print(fraud_risk_agent.format_analysis_report(analysis2))
        
        print(f"\n✅ Test 2 Complete - Threat Level: {analysis2.threat_level.value.upper()}")
        print(f"   Confidence: {analysis2.confidence_score:.0%}")
        print(f"   Category: {analysis2.fraud_category.value}")
    except Exception as e:
        print(f"\n❌ Test 2 Failed: {e}")
    
    # Test Case 3: Low risk message
    print("\n\n📋 TEST CASE 3: Legitimate Message")
    print("-" * 70)
    message3 = "Your parcel will arrive tomorrow between 9am-5pm. Track it at dtlogistics.com.au with code ABC123"
    sender3 = "notifications@dtlogistics.com.au"
    
    print(f"Message: {message3}")
    print(f"Sender: {sender3}")
    print("\n🔍 Analyzing...")
    
    try:
        analysis3 = await analyze_with_fraud_agent(message3, sender3)
        print(fraud_risk_agent.format_analysis_report(analysis3))
        
        print(f"\n✅ Test 3 Complete - Threat Level: {analysis3.threat_level.value.upper()}")
        print(f"   Confidence: {analysis3.confidence_score:.0%}")
        print(f"   Category: {analysis3.fraud_category.value}")
    except Exception as e:
        print(f"\n❌ Test 3 Failed: {e}")
    
    print("\n" + "="*70)
    print("🎉 FRAUD DETECTION TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_fraud_detection())
