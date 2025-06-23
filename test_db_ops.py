"""
Test script for Database Operations
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.db_ops import execute_select_query, test_database_connection

async def test_db_operations():
    """Test the database operations functionality"""
    print("🧪 Testing Database Operations")
    print("=" * 50)
    
    # Test 1: Database connection
    print("\n📤 Test 1: Database Connection")
    try:
        result = await test_database_connection()
        print(f"✅ Connection Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        if result.get('database_version'):
            print(f"   Database Version: {result.get('database_version')[:50]}...")
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("⚠️  Make sure PostgreSQL is running and DATABASE_URL is configured")
        return
    
    # Test 2: Valid SELECT queries
    test_queries = [
        "SELECT 1 as test_value",
        "SELECT current_timestamp as current_time",
        "SELECT version() as db_version",
    ]
    
    for i, query in enumerate(test_queries, 2):
        print(f"\n📤 Test {i}: {query}")
        try:
            result = await execute_select_query(query)
            print(f"✅ Status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"   Rows: {result.get('metadata', {}).get('row_count', 0)}")
                print(f"   Columns: {result.get('metadata', {}).get('columns', [])}")
                if result.get('data'):
                    print(f"   Sample Data: {result['data'][0] if result['data'] else 'None'}")
            else:
                print(f"   Error: {result.get('message')}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test 3: Invalid queries (should be rejected)
    invalid_queries = [
        "UPDATE users SET name = 'test'",
        "DELETE FROM products",
        "INSERT INTO orders VALUES (1, 'test')",
        "DROP TABLE users"
    ]
    
    print(f"\n📤 Test {len(test_queries) + 2}: Invalid Queries (Should be rejected)")
    for query in invalid_queries:
        print(f"   Testing: {query}")
        try:
            result = await execute_select_query(query)
            if result.get('status') == 'error':
                print(f"   ✅ Correctly rejected: {result.get('message')}")
            else:
                print(f"   ❌ Should have been rejected but wasn't")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
    
    print("\n🎉 Database Operations test completed!")

if __name__ == "__main__":
    asyncio.run(test_db_operations()) 