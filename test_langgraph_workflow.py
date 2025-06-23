"""
Test script for LangGraph Workflow Integration
"""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.orchestrator import OrchestratorAgent
from workflows.select_query_flow import select_query_workflow

async def test_langgraph_workflow():
    """Test the complete LangGraph workflow integration"""
    print("🧪 Testing LangGraph Workflow Integration")
    print("=" * 60)
    
    # Test 1: Direct workflow testing
    print("\n📤 Test 1: Direct Workflow Testing")
    print("-" * 40)
    
    test_queries = [
        "SELECT 1 as test_value",
        "SELECT current_timestamp as now",
        "show me all users",  # This should get helpful message
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test 1.{i}: {query}")
        try:
            result = await select_query_workflow.run(query)
            print(f"✅ Status: {result.get('status')}")
            print(f"   Workflow: {result.get('workflow')}")
            print(f"   SQL Query: {result.get('sql_query')}")
            
            results = result.get('results', {})
            if results.get('status') == 'success':
                print(f"   Data Rows: {len(results.get('data', []))}")
                print(f"   Columns: {results.get('metadata', {}).get('columns', [])}")
            else:
                print(f"   Message: {results.get('message', 'No message')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 2: Orchestrator integration
    print(f"\n📤 Test 2: Orchestrator Integration")
    print("-" * 40)
    
    orchestrator = OrchestratorAgent()
    
    integration_queries = [
        "SELECT version() as db_version",
        "show me the database version",
        "SELECT 42 as answer",
        "update users set active = true",  # Should be routed to destructive handler
    ]
    
    for i, query in enumerate(integration_queries, 1):
        print(f"\n🔍 Test 2.{i}: {query}")
        try:
            response = await orchestrator.process_query(query)
            print(f"✅ Status: {response.get('status')}")
            print(f"   Type: {response.get('type')}")
            print(f"   Workflow: {response.get('workflow', 'N/A')}")
            
            if response.get('type') == 'SELECT':
                print(f"   SQL Query: {response.get('sql_query', 'N/A')}")
                if response.get('data'):
                    print(f"   Data Rows: {len(response.get('data', []))}")
                    print(f"   Sample Data: {response['data'][0] if response['data'] else 'None'}")
            
            print(f"   Message: {response.get('message', 'No message')}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 3: Error handling
    print(f"\n📤 Test 3: Error Handling")
    print("-" * 40)
    
    error_queries = [
        "SELECT * FROM nonexistent_table",
        "SELECT invalid syntax query",
        "",  # Empty query
    ]
    
    for i, query in enumerate(error_queries, 1):
        print(f"\n🔍 Test 3.{i}: {query if query else '(empty query)'}")
        try:
            response = await orchestrator.process_query(query)
            print(f"✅ Status: {response.get('status')}")
            print(f"   Message: {response.get('message', 'No message')}")
            
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
    
    print("\n🎉 LangGraph Workflow Integration test completed!")
    print("\n📊 Summary:")
    print("✅ Direct workflow execution tested")
    print("✅ Orchestrator integration tested") 
    print("✅ Error handling tested")
    print("✅ Intent routing tested")

if __name__ == "__main__":
    asyncio.run(test_langgraph_workflow()) 