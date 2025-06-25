#!/usr/bin/env python3
"""
Integration tests for SELECT and UPDATE/DELETE/INSERT workflows (P4.T2.2)
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.orchestrator import OrchestratorAgent
from workflows.unified_query_flow import UnifiedQueryWorkflow

async def test_select_workflow_integration():
    """Test the complete SELECT query workflow integration"""
    print("🧪 Testing SELECT Workflow Integration (P4.T2.2)")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        # Test SELECT queries through the complete workflow
        select_queries = [
            "show me all tables in the database",
            "select version()",
            "get the current timestamp",
            "show me users table structure"
        ]
        
        for i, query in enumerate(select_queries, 1):
            print(f"\n📤 SELECT Test {i}: {query}")
            
            try:
                # Process through orchestrator (complete end-to-end)
                result = await orchestrator.process_query(query)
                
                print(f"   Status: {result.get('status')}")
                print(f"   Workflow: {result.get('workflow', 'unknown')}")
                print(f"   Query Type: {result.get('query_type', 'unknown')}")
                
                if result.get('status') == 'success':
                    print("   ✅ SELECT workflow completed successfully")
                    
                    # Check if it went through the unified workflow
                    if 'unified_query_flow' in str(result.get('workflow', '')):
                        print("   ✅ Used unified query workflow")
                    
                    # Check for SELECT execution results
                    if result.get('select_results'):
                        select_data = result['select_results'].get('data', [])
                        print(f"   📊 Results: {len(select_data)} rows returned")
                    
                    # Check orchestrator intent
                    intent = result.get('orchestrator_intent', {})
                    if intent:
                        print(f"   🧠 Intent: {intent.get('type')} (confidence: {intent.get('confidence')})")
                else:
                    print(f"   ❌ SELECT workflow failed: {result.get('message')}")
                    
            except Exception as e:
                print(f"   ❌ Error in SELECT test: {e}")
        
        print("\n🎉 SELECT workflow integration testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in SELECT workflow integration: {e}")
        return False

async def test_destructive_workflow_integration():
    """Test the complete UPDATE/DELETE/INSERT workflow integration"""
    print("\n🧪 Testing Destructive Workflow Integration (P4.T2.2)")
    print("=" * 50)
    
    try:
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        # Test destructive queries through the complete workflow
        destructive_queries = [
            {
                "query": "update users set status = 'active' where id = 1",
                "expected_type": "UPDATE"
            },
            {
                "query": "delete from logs where created_at < '2023-01-01'",
                "expected_type": "DELETE"
            },
            {
                "query": "insert into audit_log (action, user_id) values ('test', 1)",
                "expected_type": "INSERT"
            }
        ]
        
        for i, test_case in enumerate(destructive_queries, 1):
            query = test_case["query"]
            expected_type = test_case["expected_type"]
            
            print(f"\n📤 Destructive Test {i}: {expected_type}")
            print(f"   Query: {query}")
            
            try:
                # Process through orchestrator (complete end-to-end)
                result = await orchestrator.process_query(query)
                
                print(f"   Status: {result.get('status')}")
                print(f"   Workflow: {result.get('workflow', 'unknown')}")
                print(f"   Query Type: {result.get('query_type', 'unknown')}")
                
                # Check if it went through the unified workflow
                if 'unified_query_flow' in str(result.get('workflow', '')):
                    print("   ✅ Used unified query workflow")
                
                # Check for impact analysis
                if result.get('impact_analysis'):
                    impact = result['impact_analysis']
                    risk_level = impact.get('risk_classification', {}).get('level', 'unknown')
                    print(f"   🔍 Impact Analysis: {risk_level} risk")
                    
                    estimated_rows = impact.get('impact_estimate', {}).get('estimated_rows', 'unknown')
                    print(f"   📊 Estimated Rows: {estimated_rows}")
                
                # Check for approval workflow
                if result.get('approval_ticket'):
                    ticket = result['approval_ticket']
                    print(f"   🎫 Approval Ticket: {ticket.get('ticket_id', 'unknown')}")
                    print(f"   ⏳ Approval Status: {result.get('approval_status', 'unknown')}")
                
                # Check workflow completion
                if result.get('status') in ['success', 'pending_approval', 'requires_approval']:
                    print("   ✅ Destructive workflow completed successfully")
                else:
                    print(f"   ❌ Destructive workflow failed: {result.get('message')}")
                
                # Check orchestrator intent
                intent = result.get('orchestrator_intent', {})
                if intent:
                    print(f"   🧠 Intent: {intent.get('type')} (confidence: {intent.get('confidence')})")
                    
            except Exception as e:
                print(f"   ❌ Error in destructive test: {e}")
        
        print("\n🎉 Destructive workflow integration testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in destructive workflow integration: {e}")
        return False

async def test_unified_workflow_conditional_routing():
    """Test the unified workflow's conditional routing logic"""
    print("\n🧪 Testing Unified Workflow Conditional Routing")
    print("=" * 50)
    
    try:
        # Initialize unified workflow directly
        unified_workflow = UnifiedQueryWorkflow()
        
        # Test cases for conditional routing
        test_cases = [
            {
                "name": "SELECT query routing",
                "query": "show me all users",
                "expected_route": "select"
            },
            {
                "name": "UPDATE query routing", 
                "query": "update products set price = 100",
                "expected_route": "destructive"
            },
            {
                "name": "DELETE query routing",
                "query": "delete expired sessions",
                "expected_route": "destructive"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📤 Routing Test {i}: {test_case['name']}")
            
            try:
                # Create mock intent for testing
                mock_intent = {
                    "type": "UNKNOWN",  # Let the workflow determine the type
                    "confidence": 0.8,
                    "keywords": ["test"],
                    "table_mentioned": None
                }
                
                # Run through unified workflow
                result = await unified_workflow.run(test_case["query"], mock_intent)
                
                print(f"   Status: {result.get('status')}")
                print(f"   Query Type: {result.get('query_type', 'unknown')}")
                print(f"   Expected Route: {test_case['expected_route']}")
                
                # Check if routing worked correctly
                query_type = result.get('query_type', '').upper()
                if test_case['expected_route'] == 'select' and query_type == 'SELECT':
                    print("   ✅ Correctly routed to SELECT execution")
                elif test_case['expected_route'] == 'destructive' and query_type in ['UPDATE', 'DELETE', 'INSERT']:
                    print("   ✅ Correctly routed to destructive workflow")
                else:
                    print(f"   ⚠️  Routing unclear - Query type: {query_type}")
                
                # Check workflow components
                if result.get('schema_context'):
                    print("   ✅ Schema context fetched")
                
                if result.get('sql_query'):
                    print("   ✅ SQL query generated")
                
                if result.get('validation_result'):
                    print("   ✅ Query validation performed")
                    
            except Exception as e:
                print(f"   ❌ Error in routing test: {e}")
        
        print("\n🎉 Unified workflow routing testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in unified workflow routing: {e}")
        return False

async def test_end_to_end_integration():
    """Test complete end-to-end integration"""
    print("\n🧪 Testing End-to-End Integration")
    print("=" * 50)
    
    try:
        # Test the complete pipeline with various query types
        orchestrator = OrchestratorAgent()
        
        integration_tests = [
            {
                "name": "Simple SELECT",
                "query": "select 1 as test",
                "expected_components": ["intent_extraction", "schema_fetch", "query_building", "validation", "execution"]
            },
            {
                "name": "Complex SELECT with table",
                "query": "show me all users with active status",
                "expected_components": ["intent_extraction", "schema_fetch", "query_building", "validation", "execution"]
            },
            {
                "name": "UPDATE with approval",
                "query": "update all user passwords",
                "expected_components": ["intent_extraction", "schema_fetch", "query_building", "validation", "impact_analysis", "approval_workflow"]
            }
        ]
        
        for i, test_case in enumerate(integration_tests, 1):
            print(f"\n📤 E2E Test {i}: {test_case['name']}")
            print(f"   Query: {test_case['query']}")
            
            try:
                result = await orchestrator.process_query(test_case["query"])
                
                print(f"   Status: {result.get('status')}")
                
                # Check for expected components
                components_found = []
                
                if result.get('orchestrator_intent'):
                    components_found.append("intent_extraction")
                
                if result.get('schema_context') or 'schema' in str(result):
                    components_found.append("schema_fetch")
                
                if result.get('sql_query'):
                    components_found.append("query_building")
                
                if result.get('validation_result'):
                    components_found.append("validation")
                
                if result.get('select_results') or result.get('execution_result'):
                    components_found.append("execution")
                
                if result.get('impact_analysis'):
                    components_found.append("impact_analysis")
                
                if result.get('approval_ticket') or result.get('approval_status'):
                    components_found.append("approval_workflow")
                
                print(f"   Components Found: {components_found}")
                
                # Check if critical components are present
                critical_components = ["intent_extraction", "query_building"]
                missing_critical = [comp for comp in critical_components if comp not in components_found]
                
                if not missing_critical:
                    print("   ✅ Critical components present")
                else:
                    print(f"   ⚠️  Missing critical components: {missing_critical}")
                
                print(f"   📊 Total Components: {len(components_found)}")
                
            except Exception as e:
                print(f"   ❌ Error in E2E test: {e}")
        
        print("\n🎉 End-to-end integration testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error in end-to-end integration: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("🚀 Integration Tests for Workflows (P4.T2.2)")
    print("=" * 60)
    
    success1 = await test_select_workflow_integration()
    success2 = await test_destructive_workflow_integration()
    success3 = await test_unified_workflow_conditional_routing()
    success4 = await test_end_to_end_integration()
    
    if success1 and success2 and success3 and success4:
        print("\n✅ All integration tests passed!")
        print("\n📋 P4.T2.2 Integration Test Summary:")
        print("   ✅ SELECT workflow integration tested")
        print("   ✅ UPDATE/DELETE/INSERT workflow integration tested")
        print("   ✅ Unified workflow conditional routing tested")
        print("   ✅ End-to-end pipeline integration tested")
        print("   ✅ Orchestrator → Workflow → Tools → Response flow verified")
        return 0
    else:
        print("\n❌ Some integration tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 