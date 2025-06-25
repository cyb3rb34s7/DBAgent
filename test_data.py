#!/usr/bin/env python3
"""Test if there's data in the users table"""

import asyncio
import sys
import os

# Add src to Python path
sys.path.append('src')

from tools.db_ops import execute_select_query

async def test_data():
    print("Testing database data...")
    print("=" * 50)
    
    queries = [
        "SELECT COUNT(*) as total_users FROM users",
        "SELECT COUNT(*) as clients FROM users WHERE role = 'client'", 
        "SELECT COUNT(*) as active_clients FROM users WHERE role = 'client' AND status = 'active'",
        "SELECT * FROM users LIMIT 3"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            result = await execute_select_query(query)
            print(f"Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', [])
                print(f"Rows returned: {len(data)}")
                if data:
                    print(f"Sample data: {data[0] if len(data) > 0 else 'None'}")
            else:
                print(f"Error: {result.get('message')}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_data()) 