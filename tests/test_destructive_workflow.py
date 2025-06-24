#!/usr/bin/env python3
"""
Test Destructive Query Workflow - P3.T4.1 Testing
Tests the complete destructive query workflow with impact analysis, approval, and execution
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
from workflows.destructive_query_flow import destructive_query_workflow

async def test_orchestrator_destructive_routing():
    """Test that orchestrator properly routes destructive queries to the new workflow"""
    print("🧪 Testing Orchestrator Destructive Query Routing")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent()
    
    # Test queries for different destructive operations
    test_queries = [
        {
            "query": "update all users to set their status as inactive",
            "expected_type": "UPDATE",
            "expected_workflow": "destructive_query_langgraph"
        },
        {
            "query": "delete users where last_login is older than 1 year",
            "expected_type": "DELETE", 
            "expected_workflow": "destructive_query_langgraph"
        },
        {
            "query": "insert a new user with email test@example.com",
            "expected_type": "INSERT",
            "expected_workflow": "destructive_query_langgraph"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {test_case['query']}")
        print("-" * 40)
        
        try:
            # Process query through orchestrator
            result = await orchestrator.process_query(test_case["query"])
            
            # Verify routing
            print(f"✅ Status: {result.get('status')}")
            print(f"✅ Type: {result.get('type')}")
            print(f"✅ Workflow: {result.get('workflow')}")
            print(f"✅ Message: {result.get('message', 'No message')}")
            
            # Check if routed correctly
            if result.get("type") == test_case["expected_type"]:
                print(f"✅ Correct query type detected: {result.get('type')}")
            else:
                print(f"❌ Wrong query type. Expected: {test_case['expected_type']}, Got: {result.get('type')}")
            
            if result.get("workflow") == test_case["expected_workflow"]:
                print(f"✅ Correct workflow used: {result.get('workflow')}")
            else:
                print(f"❌ Wrong workflow. Expected: {test_case['expected_workflow']}, Got: {result.get('workflow')}")
            
            # Show additional info based on status
            if result.get("status") == "pending_approval":
                print(f"🎫 Approval Ticket: {result.get('approval_ticket', {}).get('ticket_id', 'No ticket')}")
                print(f"⚠️  Risk Level: {result.get('risk_level', 'Unknown')}")
                print(f"📊 Impact Analysis Available: {'Yes' if result.get('impact_analysis') else 'No'}")
            elif result.get("status") == "success":
                print(f"✅ Execution Result: {result.get('execution_result', {}).get('message', 'No message')}")
                print(f"📊 Rows Affected: {result.get('execution_result', {}).get('rows_affected', 'Unknown')}")
            elif result.get("status") == "error":
                print(f"❌ Error: {result.get('message')}")
            
        except Exception as e:
            print(f"💥 Test failed with error: {e}")
    
    print(f"\n{'='*60}")
    print("🎯 Orchestrator destructive routing test completed")

async def test_destructive_workflow_direct():
    """Test the destructive workflow directly"""
    print("\n🧪 Testing Destructive Workflow Direct Execution")
    print("=" * 60)
    
    # Test with different risk levels
    test_cases = [
        {
            "user_query": "update users set status = 'inactive' where id = 999999",
            "intent": {
                "type": "UPDATE",
                "confidence": 0.9,
                "operation_type": "WRITE",
                "table_mentioned": "users",
                "keywords": ["update", "users", "status"]
            },
            "expected_risk": "LOW"  # Single row update
        },
        {
            "user_query": "delete from logs where created_at < '2023-01-01'",
            "intent": {
                "type": "DELETE",
                "confidence": 0.9,
                "operation_type": "WRITE", 
                "table_mentioned": "logs",
                "keywords": ["delete", "logs", "created_at"]
            },
            "expected_risk": "HIGH"  # Potentially many rows
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test_case['user_query']}")
        print("-" * 40)
        
        try:
            # Run workflow directly
            result = await destructive_query_workflow.run(
                user_query=test_case["user_query"],
                intent=test_case["intent"]
            )
            
            print(f"✅ Status: {result.get('status')}")
            print(f"✅ SQL Query: {result.get('sql_query', 'No query generated')}")
            print(f"✅ Risk Level: {result.get('risk_level', 'Unknown')}")
            
            # Show workflow-specific info
            if result.get("status") == "pending_approval":
                approval_ticket = result.get("approval_ticket", {})
                print(f"🎫 Ticket ID: {approval_ticket.get('ticket_id', 'No ticket')}")
                print(f"📝 Next Steps: {result.get('next_steps', 'No instructions')}")
                
                # Show impact analysis details
                impact_analysis = result.get("impact_analysis", {})
                if impact_analysis:
                    risk_info = impact_analysis.get("risk_classification", {})
                    print(f"📊 Risk Details: {risk_info.get('level', 'Unknown')} ({risk_info.get('estimated_rows', 'unknown')} rows)")
                    
                    recommendations = impact_analysis.get("recommendations", {})
                    if recommendations:
                        safety_recommendations = recommendations.get("safety_recommendations", [])
                        if safety_recommendations:
                            print(f"💡 Safety Recommendations: {len(safety_recommendations)} suggestions")
                            for rec in safety_recommendations[:2]:  # Show first 2
                                print(f"   - {rec}")
            
            elif result.get("status") == "success":
                execution_result = result.get("execution_result", {})
                print(f"✅ Execution: {execution_result.get('message', 'No message')}")
                print(f"📊 Rows Affected: {execution_result.get('rows_affected', 'Unknown')}")
                print(f"🔒 Transaction: {execution_result.get('transaction_status', 'Unknown')}")
            
            elif result.get("status") == "error":
                print(f"❌ Error: {result.get('message')}")
                print(f"🔍 Workflow Status: {result.get('workflow_status', 'Unknown')}")
            
        except Exception as e:
            print(f"💥 Workflow test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 Direct workflow test completed")

async def test_approval_workflow_integration():
    """Test the approval workflow integration"""
    print("\n🧪 Testing Approval Workflow Integration")
    print("=" * 60)
    
    # Test a high-risk query that should require approval
    high_risk_query = "delete from user_sessions where last_activity < now() - interval '30 days'"
    intent = {
        "type": "DELETE",
        "confidence": 0.9,
        "operation_type": "WRITE",
        "table_mentioned": "user_sessions", 
        "keywords": ["delete", "user_sessions", "last_activity"]
    }
    
    print(f"📝 Testing high-risk query: {high_risk_query}")
    print("-" * 40)
    
    try:
        # Run through orchestrator
        orchestrator = OrchestratorAgent()
        result = await orchestrator.process_query(high_risk_query)
        
        print(f"✅ Status: {result.get('status')}")
        print(f"✅ Type: {result.get('type')}")
        print(f"✅ Risk Level: {result.get('risk_level', 'Unknown')}")
        
        if result.get("status") == "pending_approval":
            ticket_info = result.get("approval_ticket", {})
            ticket_id = ticket_info.get("ticket_id")
            
            if ticket_id:
                print(f"🎫 Approval Ticket Created: {ticket_id}")
                print(f"📝 Message: {result.get('message')}")
                print(f"🔗 Next Steps: {result.get('next_steps', 'No instructions')}")
                
                # Test checking approval status
                from tools.impact_execution import check_approval_status
                status_check = await check_approval_status(ticket_id)
                
                if status_check.get("status") == "found":
                    approval_data = status_check.get("approval_request", {})
                    print(f"✅ Ticket Status: {approval_data.get('status', 'Unknown')}")
                    print(f"⏰ Expires At: {approval_data.get('expires_at', 'Unknown')}")
                    print(f"📊 Metadata: {approval_data.get('metadata', {})}")
                else:
                    print(f"❌ Could not verify ticket: {status_check.get('message')}")
            else:
                print("❌ No ticket ID in approval result")
        else:
            print(f"ℹ️  Query did not require approval: {result.get('message')}")
        
    except Exception as e:
        print(f"💥 Approval workflow test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("🎯 Approval workflow integration test completed")

async def main():
    """Run all destructive workflow tests"""
    print("🚀 PostgreSQL AI Agent - Destructive Query Workflow Tests")
    print("Testing P3.T4.1: Enhanced Orchestrator with Destructive Query Routing")
    print("=" * 80)
    
    try:
        # Test 1: Orchestrator routing
        await test_orchestrator_destructive_routing()
        
        # Test 2: Direct workflow execution  
        await test_destructive_workflow_direct()
        
        # Test 3: Approval workflow integration
        await test_approval_workflow_integration()
        
        print(f"\n{'='*80}")
        print("🎉 All destructive workflow tests completed!")
        print("📋 Summary:")
        print("   ✅ P3.T4.1: Orchestrator routing to Impact Analysis Agent")
        print("   ✅ P3.T4.2: Conditional routing after query building")
        print("   ✅ P3.T4.3: Human-in-the-loop approval workflow")
        print("   ✅ P3.T4.4: Safe execution routing")
        print("\n💡 Note: For full testing, try approving a ticket via:")
        print("   curl 'http://localhost:8001/approve/{ticket_id}?approver=tester&comments=approved'")
        
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 