"""
Test script for Query Builder Agent
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from agents.query_builder import get_query_builder
from tools.db_ops import validate_query, build_sql_query
from utils.gemini_client import get_gemini_client

async def test_query_builder():
    """Test the QueryBuilderAgent functionality"""
    print("🧪 Testing Query Builder Agent")
    print("=" * 50)
    
    query_builder = get_query_builder()
    gemini_client = get_gemini_client()
    
    # Test 1: Query validation
    print("\n📤 Test 1: Query Validation")
    test_queries = [
        "SELECT * FROM users",
        "SELECT name, email FROM users WHERE status = 'active'",
        "UPDATE users SET status = 'inactive'",
        "DELETE FROM users WHERE id = 1",
        "INSERT INTO users (name, email) VALUES ('test', 'test@example.com')",
        "DROP TABLE users",  # Should be invalid
        "",  # Empty query
        "INVALID SQL SYNTAX"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Test 1.{i}: {query[:50]}{'...' if len(query) > 50 else ''}")
        try:
            result = await validate_query(query)
            print(f"      Valid: {result.get('is_valid')}")
            print(f"      Type: {result.get('query_type')}")
            print(f"      Complexity: {result.get('complexity')}")
            if result.get('issues'):
                print(f"      Issues: {result.get('issues')}")
            if result.get('suggestions'):
                print(f"      Suggestions: {result.get('suggestions')[:2]}")  # Show first 2
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 2: Intent extraction and SQL building
    print("\n📤 Test 2: SQL Query Building from Intent")
    test_intents = [
        {
            "intent": "SELECT",
            "confidence": 0.9,
            "keywords": ["show", "users", "active"],
            "table_mentioned": "users",
            "operation_type": "READ"
        },
        {
            "intent": "SELECT",
            "confidence": 0.8,
            "keywords": ["get", "orders", "customer"],
            "table_mentioned": "orders",
            "operation_type": "READ"
        },
        {
            "intent": "SELECT",
            "confidence": 0.7,
            "keywords": ["count", "trades", "today"],
            "table_mentioned": "trades",
            "operation_type": "READ"
        }
    ]
    
    for i, intent_data in enumerate(test_intents, 1):
        print(f"\n   Test 2.{i}: Intent - {intent_data['intent']} for {intent_data.get('table_mentioned')}")
        try:
            result = await build_sql_query(intent_data)
            print(f"      Status: {result.get('status')}")
            if result.get('status') == 'success':
                print(f"      Generated SQL: {result.get('sql_query')}")
                print(f"      Schema used: {result.get('schema_used', {}).get('tables_count')} tables")
                print(f"      Cached: {result.get('schema_used', {}).get('cached')}")
                
                validation = result.get('validation', {})
                print(f"      Valid: {validation.get('is_valid')}")
                print(f"      Complexity: {validation.get('complexity')}")
                
                alternatives = result.get('alternatives', [])
                if alternatives:
                    print(f"      Alternatives: {len(alternatives)} generated")
                    for alt in alternatives[:1]:  # Show first alternative
                        print(f"        - {alt.get('type')}: {alt.get('query')[:50]}...")
            else:
                print(f"      Error: {result.get('message')}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 3: Direct Gemini intent extraction
    print("\n📤 Test 3: Direct Intent Extraction with Gemini")
    test_natural_queries = [
        "show me all users who are active",
        "get the total number of trades for today",
        "find users with email containing 'gmail'",
        "list all orders from last week"
    ]
    
    for i, query in enumerate(test_natural_queries, 1):
        print(f"\n   Test 3.{i}: '{query}'")
        try:
            # Extract intent using Gemini
            intent_result = await gemini_client.extract_intent(query)
            print(f"      Intent: {intent_result.get('intent')}")
            print(f"      Confidence: {intent_result.get('confidence')}")
            print(f"      Table mentioned: {intent_result.get('table_mentioned')}")
            print(f"      Keywords: {intent_result.get('keywords')}")
            
            # Build SQL from extracted intent
            if intent_result.get('intent') == 'SELECT':
                sql_result = await build_sql_query(intent_result)
                if sql_result.get('status') == 'success':
                    print(f"      Generated SQL: {sql_result.get('sql_query')}")
                    validation = sql_result.get('validation', {})
                    print(f"      Valid: {validation.get('is_valid')}")
                else:
                    print(f"      SQL Generation Error: {sql_result.get('message')}")
            else:
                print(f"      Non-SELECT intent - skipping SQL generation")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    # Test 4: Query optimization suggestions
    print("\n📤 Test 4: Query Optimization")
    optimization_test_queries = [
        "SELECT * FROM users WHERE name LIKE '%john%'",
        "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id ORDER BY o.total",
        "SELECT COUNT(*) FROM trades GROUP BY user_id"
    ]
    
    for i, query in enumerate(optimization_test_queries, 1):
        print(f"\n   Test 4.{i}: {query}")
        try:
            # Get schema context for optimization
            from tools.db_ops import fetch_schema_context
            schema_result = await fetch_schema_context()
            
            if schema_result.get('status') == 'success':
                schema_context = schema_result.get('schema_context', {})
                opt_result = await query_builder.optimize_query(query, schema_context)
                
                if opt_result.get('status') == 'success':
                    optimizations = opt_result.get('optimizations', {})
                    print(f"      Suggestions: {optimizations.get('suggestions', [])}")
                    print(f"      Performance tips: {optimizations.get('performance_tips', [])}")
                else:
                    print(f"      Optimization error: {opt_result.get('message')}")
            else:
                print(f"      Schema fetch error: {schema_result.get('message')}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print("\n🎉 Query Builder Agent test completed!")

if __name__ == "__main__":
    asyncio.run(test_query_builder()) 