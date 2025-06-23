"""
Test script for Schema Context Fetching
"""

import asyncio
import sys
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.db_ops import fetch_schema_context

async def test_schema_context():
    """Test the schema context fetching functionality"""
    print("🧪 Testing Schema Context Fetching")
    print("=" * 50)
    
    # Test 1: Fetch all tables without samples
    print("\n📤 Test 1: Fetch all tables (no samples)")
    try:
        result = await fetch_schema_context()
        print(f"✅ Status: {result.get('status')}")
        if result.get('status') == 'success':
            schema = result.get('schema_context', {})
            print(f"   Total tables: {schema.get('metadata', {}).get('total_tables', 0)}")
            print(f"   Tables found: {list(schema.get('tables', {}).keys())}")
            print(f"   Relationships: {len(schema.get('relationships', []))}")
            
            # Show details for first table if any
            if schema.get('tables'):
                first_table = list(schema['tables'].keys())[0]
                table_info = schema['tables'][first_table]
                print(f"   Sample table '{first_table}':")
                print(f"     - Columns: {len(table_info.get('columns', {}))}")
                print(f"     - Primary keys: {table_info.get('primary_keys', [])}")
                print(f"     - Foreign keys: {len(table_info.get('foreign_keys', []))}")
        else:
            print(f"   Error: {result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Fetch specific tables with samples (if any tables exist)
    print("\n📤 Test 2: Fetch specific tables with samples")
    try:
        # First get all tables to see what's available
        all_tables_result = await fetch_schema_context()
        if all_tables_result.get('status') == 'success':
            available_tables = list(all_tables_result.get('schema_context', {}).get('tables', {}).keys())
            
            if available_tables:
                # Test with first available table
                test_table = available_tables[0]
                result = await fetch_schema_context(table_names=[test_table], include_samples=True)
                print(f"✅ Status: {result.get('status')}")
                if result.get('status') == 'success':
                    schema = result.get('schema_context', {})
                    print(f"   Filtered for table: {test_table}")
                    print(f"   Tables returned: {list(schema.get('tables', {}).keys())}")
                    
                    # Show sample data if available
                    if schema.get('samples') and test_table in schema['samples']:
                        samples = schema['samples'][test_table]
                        print(f"   Sample data rows: {len(samples)}")
                        if samples:
                            print(f"   Sample row: {samples[0]}")
                    else:
                        print("   No sample data available")
                else:
                    print(f"   Error: {result.get('message')}")
            else:
                print("   No tables available to test with")
        else:
            print("   Could not get available tables for testing")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Test with non-existent table
    print("\n📤 Test 3: Test with non-existent table")
    try:
        result = await fetch_schema_context(table_names=['nonexistent_table'])
        print(f"✅ Status: {result.get('status')}")
        if result.get('status') == 'success':
            schema = result.get('schema_context', {})
            print(f"   Tables found: {len(schema.get('tables', {}))}")
            print(f"   Should be empty for non-existent table")
        else:
            print(f"   Error: {result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Show detailed schema structure for one table
    print("\n📤 Test 4: Detailed schema structure")
    try:
        result = await fetch_schema_context()
        if result.get('status') == 'success':
            schema = result.get('schema_context', {})
            if schema.get('tables'):
                print("   Detailed schema structure:")
                print(json.dumps(schema, indent=2, default=str)[:1000] + "...")
            else:
                print("   No tables to show detailed structure")
        else:
            print(f"   Error: {result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Schema context fetching test completed!")

if __name__ == "__main__":
    asyncio.run(test_schema_context()) 