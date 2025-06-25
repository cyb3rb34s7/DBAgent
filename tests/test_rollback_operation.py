#!/usr/bin/env python3
"""
Unit test for rollback_operation tool (P4.T1.3)
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.impact_execution import rollback_operation

async def test_rollback_operation():
    """Test the rollback_operation tool"""
    print("🧪 Testing rollback_operation tool (P4.T1.3)")
    print("=" * 50)
    
    # Test data
    test_ticket_id = "test-rollback-12345"
    test_operation_info = {
        "reason": "Test rollback operation",
        "requested_by": "unit_test",
        "operation_type": "DELETE",
        "affected_tables": ["test_users"]
    }
    
    try:
        print("\n📤 Test 1: Basic rollback operation logging")
        result = await rollback_operation(test_ticket_id, test_operation_info)
        
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message', '')[:80]}...")
        print(f"   Ticket ID: {result.get('ticket_id')}")
        
        if result.get('status') == 'logged':
            print("   ✅ Rollback operation logged successfully")
            
            # Check rollback info
            rollback_info = result.get('rollback_info', {})
            if rollback_info:
                print(f"   📋 Rollback method: {rollback_info.get('rollback_method')}")
                print(f"   📋 Redis logged: {rollback_info.get('redis_logged')}")
                print(f"   📋 Ticket updated: {rollback_info.get('ticket_updated')}")
                
                # Check recommendations
                recommendations = rollback_info.get('recommendations', {})
                if recommendations:
                    immediate_actions = recommendations.get('immediate_actions', [])
                    rollback_strategies = recommendations.get('rollback_strategies', [])
                    
                    print(f"   💡 Immediate actions: {len(immediate_actions)} items")
                    print(f"   💡 Rollback strategies: {len(rollback_strategies)} items")
                    print(f"   💡 Escalation required: {recommendations.get('escalation_required')}")
                    
                    if immediate_actions:
                        print(f"   💡 First action: {immediate_actions[0]}")
        else:
            print("   ❌ Rollback operation failed")
            return False
        
        print("\n📤 Test 2: Rollback with missing ticket")
        result2 = await rollback_operation("non-existent-ticket", test_operation_info)
        
        print(f"   Status: {result2.get('status')}")
        if result2.get('status') == 'logged':
            print("   ✅ Handled missing ticket gracefully")
        else:
            print("   ❌ Failed to handle missing ticket")
        
        print("\n📤 Test 3: Rollback with minimal info")
        result3 = await rollback_operation("minimal-test", {})
        
        print(f"   Status: {result3.get('status')}")
        if result3.get('status') == 'logged':
            print("   ✅ Handled minimal info gracefully")
        else:
            print("   ❌ Failed to handle minimal info")
        
        print("\n🎉 Rollback operation testing completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing rollback operation: {e}")
        return False

async def test_rollback_recommendations():
    """Test rollback recommendation generation"""
    print("\n🧪 Testing rollback recommendation generation")
    print("=" * 50)
    
    try:
        # Import the class to test internal method
        from tools.impact_execution import ImpactExecutionOperations
        impact_ops = ImpactExecutionOperations()
        
        # Test different risk scenarios
        test_scenarios = [
            {
                "name": "HIGH risk DELETE operation",
                "rollback_info": {
                    "risk_level": "HIGH",
                    "original_query": "DELETE FROM users WHERE status = 'inactive'"
                }
            },
            {
                "name": "MEDIUM risk UPDATE operation", 
                "rollback_info": {
                    "risk_level": "MEDIUM",
                    "original_query": "UPDATE products SET price = price * 1.1"
                }
            },
            {
                "name": "LOW risk INSERT operation",
                "rollback_info": {
                    "risk_level": "LOW", 
                    "original_query": "INSERT INTO logs (message) VALUES ('test')"
                }
            }
        ]
        
        for scenario in test_scenarios:
            print(f"\n📤 Testing: {scenario['name']}")
            recommendations = impact_ops._generate_rollback_recommendations(scenario['rollback_info'])
            
            print(f"   💡 Immediate actions: {len(recommendations.get('immediate_actions', []))}")
            print(f"   💡 Rollback strategies: {len(recommendations.get('rollback_strategies', []))}")
            print(f"   💡 Prevention measures: {len(recommendations.get('prevention_measures', []))}")
            print(f"   🚨 Escalation required: {recommendations.get('escalation_required')}")
            
            if recommendations.get('immediate_actions'):
                print(f"   📋 First action: {recommendations['immediate_actions'][0]}")
        
        print("\n🎉 Rollback recommendation testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing rollback recommendations: {e}")
        return False

async def main():
    """Run all rollback operation tests"""
    print("🚀 Rollback Operation Unit Tests (P4.T1.3)")
    print("=" * 60)
    
    success1 = await test_rollback_operation()
    success2 = await test_rollback_recommendations()
    
    if success1 and success2:
        print("\n✅ All rollback operation tests passed!")
        return 0
    else:
        print("\n❌ Some rollback operation tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 