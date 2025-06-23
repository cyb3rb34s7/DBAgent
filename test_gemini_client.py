"""
Test script for GeminiClient utility
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils.gemini_client import get_gemini_client

async def test_gemini_client():
    """Test the GeminiClient utility functionality"""
    print("🧪 Testing GeminiClient Utility")
    print("=" * 50)
    
    try:
        # Get Gemini client instance
        client = get_gemini_client()
        print("✅ GeminiClient initialized successfully")
        
        # Test 1: Basic content generation
        print("\n📤 Test 1: Basic content generation")
        response = await client.generate_content("What is the capital of France? Answer in one word.")
        print(f"✅ Response: {response}")
        
        # Test 2: Intent extraction
        print("\n📤 Test 2: Intent extraction")
        test_queries = [
            "show me all users",
            "SELECT * FROM products WHERE price > 100",
            "update users set status = 'active'",
            "delete old records from logs"
        ]
        
        for query in test_queries:
            print(f"   Query: {query}")
            intent = await client.extract_intent(query)
            print(f"   Intent: {intent.get('intent')}, Confidence: {intent.get('confidence')}")
            print(f"   Keywords: {intent.get('keywords')}")
            print(f"   Table: {intent.get('table_mentioned')}")
            print()
        
        # Test 3: SQL query building (with mock schema)
        print("\n📤 Test 3: SQL query building")
        mock_schema = """
        Tables:
        - users (id, name, email, status, created_at)
        - products (id, name, price, category, stock)
        - orders (id, user_id, product_id, quantity, order_date)
        """
        
        intent_data = {
            "intent": "SELECT",
            "confidence": 0.9,
            "keywords": ["show", "users", "active"],
            "table_mentioned": "users",
            "operation_type": "READ"
        }
        
        sql_query = await client.build_sql_query(intent_data, mock_schema)
        print(f"✅ Generated SQL: {sql_query}")
        
        print("\n🎉 GeminiClient utility test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing GeminiClient: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_gemini_client()) 