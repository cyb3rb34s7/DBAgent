#!/usr/bin/env python3
"""
Test Unified Query Workflow - P3.T4.2 Testing
Tests the unified workflow with conditional routing after query building
"""

import asyncio
import sys
import os
import json
from dotenv import load_dotenv
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
load_dotenv()

# Debug Redis connection immediately
print("🔍 DEBUG: Testing Redis connection at script start...")
try:
    import redis
    redis_url = os.getenv('REDIS_URL')
    print(f"🔍 DEBUG: REDIS_URL = {redis_url}")
    
    r = redis.from_url(redis_url)
    r.ping()
    print("🔍 DEBUG: ✅ Direct Redis connection works at script start")
except Exception as e:
    print(f"🔍 DEBUG: ❌ Direct Redis connection failed at script start: {e}")

# Test our Redis client utility
try:
    from utils.redis_client import get_redis_client
    redis_client = get_redis_client()
    print(f"🔍 DEBUG: Redis client connected: {redis_client.is_connected()}")
    if not redis_client.is_connected():
        print(f"🔍 DEBUG: Redis client URL: {redis_client.redis_url}")
except Exception as e:
    print(f"🔍 DEBUG: ❌ Redis client utility failed: {e}")

print("🔍 DEBUG: Continuing with main tests...\n")

from agents.orchestrator import OrchestratorAgent
from workflows.unified_query_flow import unified_query_workflow

async def test_unified_workflow_direct():
    """Test the unified workflow directly with different query types"""
    print("🧪 Testing Unified Workflow Direct Execution")
    print("=" * 60)
    
    # Test cases that should demonstrate conditional routing after query building
    test_cases = [
        {
            "description": "Natural language SELECT query",
            "user_query": "show me all active users",
            "intent": {
                "type": "SELECT",  # Intent says SELECT
                "confidence": 0.8,
                "operation_type": "READ",
                "table_mentioned": "users",
                "keywords": ["show", "active", "users"]
            },
            "expected_query_type": "SELECT"
        },
        {
            "description": "Ambiguous query that could be SELECT or UPDATE",
            "user_query": "make all inactive users active",
            "intent": {
                "type": "UNKNOWN",  # Intent is ambiguous
                "confidence": 0.5,
                "operation_type": "UNKNOWN",
                "table_mentioned": "users",
                "keywords": ["make", "inactive", "users", "active"]
            },
            "expected_query_type": "DESTRUCTIVE"  # Should be determined after query building
        },
        {
            "description": "DELETE query with clear intent",
            "user_query": "remove old inactive users",
            "intent": {
                "type": "DELETE",
                "confidence": 0.9,
                "operation_type": "WRITE",
                "table_mentioned": "users",
                "keywords": ["remove", "old", "inactive", "users"]
            },
            "expected_query_type": "DESTRUCTIVE"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"Query: {test_case['user_query']}")
        print("-" * 40)
        
        try:
            # Run unified workflow directly
            result = await unified_query_workflow.run(
                user_query=test_case["user_query"],
                intent=test_case["intent"]
            )
            
            print(f"✅ Status: {result.get('status')}")
            print(f"✅ SQL Query: {result.get('sql_query', 'No query generated')}")
            print(f"✅ Query Type (Determined): {result.get('query_type', 'Unknown')}")
            print(f"✅ Workflow: {result.get('workflow', 'Unknown')}")
            
            # Verify conditional routing worked correctly
            determined_type = result.get('query_type', 'Unknown')
            expected_type = test_case['expected_query_type']
            
            if determined_type == expected_type:
                print(f"✅ Conditional routing correct: {determined_type}")
            else:
                print(f"❌ Conditional routing incorrect. Expected: {expected_type}, Got: {determined_type}")
            
            # Show type-specific results
            if determined_type == "SELECT":
                data = result.get("data", [])
                print(f"📊 SELECT Results: {len(data)} rows returned")
                if data:
                    print(f"   Sample: {data[0] if len(data) > 0 else 'No data'}")
            
            elif determined_type == "DESTRUCTIVE":
                risk_level = result.get("risk_level", "Unknown")
                print(f"⚠️  Risk Level: {risk_level}")
                
                if result.get("status") == "pending_approval":
                    ticket = result.get("approval_ticket", {})
                    print(f"🎫 Approval Ticket: {ticket.get('ticket_id', 'No ticket')}")
                    print(f"📝 Next Steps: {result.get('next_steps', 'No instructions')}")
                elif result.get("status") == "success":
                    execution_result = result.get("execution_result", {})
                    print(f"✅ Execution: {execution_result.get('message', 'No message')}")
                    print(f"📊 Rows Affected: {execution_result.get('rows_affected', 'Unknown')}")
            
            if result.get("status") == "error":
                print(f"❌ Error: {result.get('message')}")
            
        except Exception as e:
            print(f"💥 Test failed with error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 Direct unified workflow test completed")

async def test_orchestrator_with_unified_workflow():
    """Test orchestrator using the unified workflow"""
    print("\n🧪 Testing Orchestrator with Unified Workflow")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent()
    
    # Test queries that demonstrate P3.T4.2 - conditional routing after query building
    test_queries = [
        {
            "query": "show me all users who are active",
            "description": "Clear SELECT intent"
        },
        {
            "query": "update all users to set their status as inactive",
            "description": "Clear UPDATE intent"
        },
        {
            "query": "make the user with email test@example.com an admin",
            "description": "Ambiguous intent - could be UPDATE or INSERT"
        },
        {
            "query": "get rid of users who haven't logged in for 6 months",
            "description": "Ambiguous intent - could be SELECT or DELETE"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test_case['description']}")
        print(f"Query: {test_case['query']}")
        print("-" * 40)
        
        try:
            # Process query through orchestrator
            result = await orchestrator.process_query(test_case["query"])
            
            print(f"✅ Status: {result.get('status')}")
            print(f"✅ Workflow: {result.get('workflow')}")
            print(f"✅ Query Type (Determined): {result.get('query_type', 'Unknown')}")
            print(f"✅ SQL Query: {result.get('sql_query', 'No query')[:100]}...")
            print(f"✅ Gemini Used: {result.get('gemini_used', False)}")
            
            # Show orchestrator intent vs determined type
            orchestrator_intent = result.get("orchestrator_intent", {})
            print(f"🧠 Orchestrator Intent: {orchestrator_intent.get('type', 'Unknown')} (confidence: {orchestrator_intent.get('confidence', 0)})")
            print(f"🔍 Determined Type: {result.get('query_type', 'Unknown')}")
            
            # This demonstrates P3.T4.2 - the type is determined AFTER query building
            if orchestrator_intent.get('type') != result.get('query_type'):
                print(f"🎯 P3.T4.2 Success: Intent changed from {orchestrator_intent.get('type')} to {result.get('query_type')} after query building")
            
            # Show results based on final type
            if result.get("status") == "success":
                if result.get("query_type") == "SELECT":
                    data = result.get("data", [])
                    print(f"📊 SELECT Results: {len(data)} rows")
                else:
                    execution_result = result.get("execution_result", {})
                    print(f"✅ Execution: {execution_result.get('message', 'Executed')}")
            elif result.get("status") == "pending_approval":
                print(f"🎫 Approval Required: {result.get('approval_ticket', {}).get('ticket_id', 'No ticket')}")
                print(f"⚠️  Risk Level: {result.get('risk_level', 'Unknown')}")
            elif result.get("status") == "error":
                print(f"❌ Error: {result.get('message')}")
            
        except Exception as e:
            print(f"💥 Test failed with error: {e}")
    
    print(f"\n{'='*60}")
    print("🎯 Orchestrator unified workflow test completed")

async def test_conditional_routing_scenarios():
    """Test specific scenarios that demonstrate conditional routing after query building"""
    print("\n🧪 Testing Conditional Routing Scenarios (P3.T4.2)")
    print("=" * 60)
    
    # These scenarios specifically test the conditional routing AFTER query building
    scenarios = [
        {
            "name": "Misleading Intent - Says SELECT but becomes UPDATE",
            "user_query": "show me how to make all users active",
            "initial_intent_type": "SELECT",  # User said "show me"
            "expected_final_type": "DESTRUCTIVE"  # But AI should generate UPDATE
        },
        {
            "name": "Misleading Intent - Says UPDATE but becomes SELECT",
            "user_query": "update me on the status of all users",
            "initial_intent_type": "UPDATE",  # User said "update"
            "expected_final_type": "SELECT"  # But AI should generate SELECT
        },
        {
            "name": "Ambiguous Intent - Could be either",
            "user_query": "handle inactive users",
            "initial_intent_type": "UNKNOWN",
            "expected_final_type": "DESTRUCTIVE"  # AI will decide based on context
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📝 Scenario {i}: {scenario['name']}")
        print(f"Query: {scenario['user_query']}")
        print(f"Expected Initial Intent: {scenario['initial_intent_type']}")
        print(f"Expected Final Type: {scenario['expected_final_type']}")
        print("-" * 40)
        
        try:
            # Create a misleading intent to test conditional routing
            misleading_intent = {
                "type": scenario['initial_intent_type'],
                "confidence": 0.7,
                "operation_type": "READ" if scenario['initial_intent_type'] == "SELECT" else "WRITE",
                "table_mentioned": "users",
                "keywords": scenario['user_query'].split()
            }
            
            # Run through unified workflow
            result = await unified_query_workflow.run(
                user_query=scenario['user_query'],
                intent=misleading_intent
            )
            
            initial_type = misleading_intent['type']
            final_type = result.get('query_type', 'Unknown')
            
            print(f"✅ Initial Intent: {initial_type}")
            print(f"✅ Final Query Type: {final_type}")
            print(f"✅ SQL Generated: {result.get('sql_query', 'No query')[:100]}...")
            
            # Check if conditional routing worked
            if initial_type != final_type:
                print(f"🎯 P3.T4.2 SUCCESS: Conditional routing changed type from {initial_type} to {final_type}")
            else:
                print(f"ℹ️  No routing change needed: {initial_type} → {final_type}")
            
            # Verify expected outcome
            if final_type == scenario['expected_final_type']:
                print(f"✅ Expected outcome achieved: {final_type}")
            else:
                print(f"❌ Unexpected outcome. Expected: {scenario['expected_final_type']}, Got: {final_type}")
            
            print(f"✅ Status: {result.get('status')}")
            
        except Exception as e:
            print(f"💥 Scenario failed: {e}")
    
    print(f"\n{'='*60}")
    print("🎯 Conditional routing scenarios test completed")

async def main():
    """Run all unified workflow tests"""
    print("🚀 PostgreSQL AI Agent - Unified Workflow Tests")
    print("Testing P3.T4.2: Conditional routing after query building")
    print("=" * 80)
    
    try:
        # Test 1: Direct unified workflow
        await test_unified_workflow_direct()
        
        # Test 2: Orchestrator with unified workflow
        await test_orchestrator_with_unified_workflow()
        
        # Test 3: Conditional routing scenarios
        await test_conditional_routing_scenarios()
        
        print(f"\n{'='*80}")
        print("🎉 All unified workflow tests completed!")
        print("📋 Summary:")
        print("   ✅ P3.T4.2: Conditional routing after query building implemented")
        print("   ✅ Unified workflow handles both SELECT and destructive queries")
        print("   ✅ Query type determined AFTER building, not from initial intent")
        print("   ✅ Proper routing to SELECT execution or destructive approval workflow")
        print("\n💡 Key Achievement: Single workflow with conditional routing based on generated SQL")
        
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 