"""
Test Script for Address Intelligence Agent
Tests AI-powered address validation with typo detection and complication prediction
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base import address_intelligence_agent

# Test cases covering various scenarios
TEST_ADDRESSES = [
    {
        "name": "Valid Sydney CBD Address",
        "address": "123 George Street, Sydney NSW 2000",
        "context": {"recipient_name": "John Smith", "service_type": "standard"},
        "expected": {"should_be_valid": True, "should_have_complications": False}
    },
    {
        "name": "Address with Typo (Mellbourne)",
        "address": "45 Collins Street, Mellbourne VIC 3000",
        "context": {"recipient_name": "Sarah Johnson", "service_type": "express"},
        "expected": {"should_be_valid": False, "typo_detected": True}
    },
    {
        "name": "Rural Address (Delivery Complication)",
        "address": "123 Outback Road, Bourke NSW 2840",
        "context": {"recipient_name": "Mike Brown", "service_type": "standard"},
        "expected": {"should_be_valid": True, "should_have_complications": True}
    },
    {
        "name": "Multi-Tenant Building (Missing Unit)",
        "address": "100 Market Street, Sydney NSW 2000",
        "context": {"recipient_name": "Tech Corp", "service_type": "express"},
        "expected": {"should_be_valid": True, "should_have_recommendations": True}
    },
    {
        "name": "Incomplete Address (Missing Postcode)",
        "address": "45 Queen Street, Brisbane",
        "context": {"recipient_name": "Jane Doe", "service_type": "standard"},
        "expected": {"should_be_valid": False, "should_have_warnings": True}
    },
    {
        "name": "Valid Melbourne Address",
        "address": "567 Bourke Street, Melbourne VIC 3000",
        "context": {"recipient_name": "David Lee", "service_type": "overnight"},
        "expected": {"should_be_valid": True, "should_have_complications": False}
    }
]


async def test_address_intelligence():
    """Run comprehensive address intelligence tests"""
    print("=" * 80)
    print("ADDRESS INTELLIGENCE AGENT - COMPREHENSIVE TEST")
    print("=" * 80)
    print("\nTesting AI-powered address validation, typo detection, and complication analysis\n")
    
    results = {
        "passed": 0,
        "failed": 0,
        "ai_available": True,
        "tests": []
    }
    
    for idx, test in enumerate(TEST_ADDRESSES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {idx}/{len(TEST_ADDRESSES)}: {test['name']}")
        print(f"{'=' * 80}")
        print(f"Address: {test['address']}")
        print(f"Context: {test['context']}")
        
        try:
            # Call AI Address Intelligence Agent
            result = await address_intelligence_agent(test['address'], test['context'])
            
            # Check if AI agent is available
            if not result.get('success'):
                print(f"\n❌ AI Agent Error: {result.get('error')}")
                results['ai_available'] = False
                results['failed'] += 1
                results['tests'].append({
                    "test": test['name'],
                    "status": "FAILED",
                    "reason": "AI agent unavailable"
                })
                continue
            
            # Display results
            print(f"\n📊 AI ANALYSIS RESULTS:")
            print(f"   ✓ Valid: {result.get('is_valid', 'Unknown')}")
            print(f"   ✓ Confidence: {result.get('confidence', 0) * 100:.0f}%")
            print(f"   ✓ Risk Level: {result.get('risk_level', 'Unknown')}")
            print(f"   ✓ Typo Detected: {result.get('typo_detected', False)}")
            
            if result.get('suggested_correction'):
                print(f"   ✓ Suggested Correction: {result['suggested_correction']}")
            
            if result.get('complications'):
                print(f"   ✓ Complications: {', '.join(result['complications'])}")
            
            if result.get('warnings'):
                print(f"   ✓ Warnings: {', '.join(result['warnings'])}")
            
            if result.get('recommendations'):
                print(f"   ✓ Recommendations: {', '.join(result['recommendations'])}")
            
            # Validate against expectations
            test_passed = True
            failures = []
            
            expected = test['expected']
            
            if 'should_be_valid' in expected:
                if result.get('is_valid') != expected['should_be_valid']:
                    test_passed = False
                    failures.append(f"Expected valid={expected['should_be_valid']}, got {result.get('is_valid')}")
            
            if expected.get('typo_detected') and not result.get('typo_detected'):
                test_passed = False
                failures.append("Expected typo detection")
            
            if expected.get('should_have_complications') and not result.get('complications'):
                test_passed = False
                failures.append("Expected delivery complications")
            
            if expected.get('should_have_recommendations') and not result.get('recommendations'):
                test_passed = False
                failures.append("Expected recommendations")
            
            if expected.get('should_have_warnings') and not result.get('warnings'):
                test_passed = False
                failures.append("Expected warnings")
            
            # Print test result
            if test_passed:
                print(f"\n✅ TEST PASSED")
                results['passed'] += 1
                results['tests'].append({
                    "test": test['name'],
                    "status": "PASSED"
                })
            else:
                print(f"\n❌ TEST FAILED:")
                for failure in failures:
                    print(f"   - {failure}")
                results['failed'] += 1
                results['tests'].append({
                    "test": test['name'],
                    "status": "FAILED",
                    "reason": '; '.join(failures)
                })
            
            # Show full AI response (truncated)
            print(f"\n📝 Full AI Response (first 300 chars):")
            print(f"   {result.get('response', 'No response')[:300]}...")
            
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            results['failed'] += 1
            results['tests'].append({
                "test": test['name'],
                "status": "EXCEPTION",
                "reason": str(e)
            })
    
    # Final Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(TEST_ADDRESSES)}")
    print(f"Passed: {results['passed']} ✅")
    print(f"Failed: {results['failed']} ❌")
    print(f"Success Rate: {results['passed'] / len(TEST_ADDRESSES) * 100:.0f}%")
    print(f"AI Agent Available: {'YES ✅' if results['ai_available'] else 'NO ❌'}")
    
    print("\n📋 DETAILED RESULTS:")
    for test in results['tests']:
        status_icon = "✅" if test['status'] == "PASSED" else "❌"
        print(f"   {status_icon} {test['test']}: {test['status']}")
        if 'reason' in test:
            print(f"      Reason: {test['reason']}")
    
    print("\n" + "=" * 80)
    
    # Return exit code
    return 0 if results['failed'] == 0 else 1


async def test_existing_functionality():
    """Test that existing address validation still works (backward compatibility)"""
    print("\n" + "=" * 80)
    print("BACKWARD COMPATIBILITY TEST")
    print("=" * 80)
    print("\nVerifying existing functionality still works...\n")
    
    # Test simple address validation without AI context
    simple_address = "100 William Street, Sydney NSW 2000"
    
    print(f"Testing simple address: {simple_address}")
    result = await address_intelligence_agent(simple_address, None)
    
    if result.get('success'):
        print(f"✅ Basic validation works: Valid={result.get('is_valid')}")
        print(f"   Confidence: {result.get('confidence', 0) * 100:.0f}%")
        return True
    else:
        print(f"❌ Basic validation failed: {result.get('error')}")
        return False


if __name__ == "__main__":
    print("\n🧪 Starting Address Intelligence Agent Tests...\n")
    
    async def run_all_tests():
        # Test new functionality
        test_result = await test_address_intelligence()
        
        # Test backward compatibility
        compat_result = await test_existing_functionality()
        
        if test_result == 0 and compat_result:
            print("\n🎉 ALL TESTS PASSED - Address Intelligence Agent is working correctly!")
            return 0
        else:
            print("\n⚠️ SOME TESTS FAILED - Please review the output above")
            return 1
    
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
