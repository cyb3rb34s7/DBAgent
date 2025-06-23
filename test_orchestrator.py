"""
Test script for OrchestratorAgent
"""

import asyncio
import sys
import os

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.orchestrator import OrchestratorAgent

async def test_orchestrator():
    """Test the OrchestratorAgent functionality"""
    print("🧪 Testing OrchestratorAgent")
    print("=" * 50)
    
    # Initialize the orchestrator
    orchestrator = OrchestratorAgent()
    
    # Test queries
    test_queries = [
        "show me all users",
        "select * from products where price > 100",
        "update users set status = 'active'",
        "delete from orders where date < '2023-01-01'",
        "insert into customers (name, email) values ('John', 'john@example.com')",
        "this is a random query that doesn't match any pattern"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📤 Test {i}: {query}")
        
        try:
            response = await orchestrator.process_query(query)
            print(f"✅ Response:")
            print(f"   Status: {response.get('status')}")
            print(f"   Type: {response.get('type')}")
            print(f"   Message: {response.get('message')}")
            
            if 'intent' in response:
                intent = response['intent']
                print(f"   Intent Type: {intent.get('type')}")
                print(f"   Confidence: {intent.get('confidence')}")
                print(f"   Keywords: {intent.get('keywords')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎉 OrchestratorAgent test completed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator()) 