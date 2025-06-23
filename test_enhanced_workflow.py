"""
Test script for Enhanced LangGraph Workflow
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.orchestrator import OrchestratorAgent
from workflows.select_query_flow import select_query_workflow
from utils.gemini_client import get_gemini_client

async def test_enhanced_workflow():
    """Test the enhanced LangGraph workflow with Gemini AI integration"""
    print("🧪 Testing Enhanced LangGraph Workflow")
    print("=" * 60)
    
    orchestrator = OrchestratorAgent()
    gemini_client = get_gemini_client()
    
    # Test 1: End-to-end orchestrator processing
    print("\n📤 Test 1: End-to-End Orchestrator Processing")
    test_queries = [
        "show me all users who are active",
        "get the total count of trades",
        "find users with gmail email addresses",
        "list all audit logs from today"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Test 1.{i}: '{query}'")
        try:
            result = await orchestrator.process_query(query)
            print(f"      Status: {result.get('status')}")
            print(f"      Type: {result.get('type')}")
            print(f"      Workflow: {result.get('workflow')}")
            print(f"      Gemini used: {result.get('gemini_used')}")
            
            if result.get('status') == 'success':
                print(f"      SQL generated: {result.get('sql_query', '')[:80]}...")
                metadata = result.get('metadata', {})
                print(f"      Rows returned: {metadata.get('row_count', 0)}")
            else:
                print(f"      Message: {result.get('message')}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print("\n🎉 Enhanced workflow testing completed!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_workflow()) 