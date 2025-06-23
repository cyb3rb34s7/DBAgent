"""
Test script for Redis Caching functionality
"""

import asyncio
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tools.db_ops import fetch_schema_context
from utils.redis_client import get_redis_client

async def test_redis_caching():
    """Test Redis caching functionality for schema data"""
    print("🧪 Testing Redis Caching for Schema Data")
    print("=" * 50)
    
    redis_client = get_redis_client()
    
    # Test 1: Check Redis connection
    print("\n📤 Test 1: Redis Connection")
    print(f"✅ Redis Connected: {redis_client.is_connected()}")
    if not redis_client.is_connected():
        print("⚠️  Redis not available - caching tests will be limited")
    
    # Test 2: First fetch (should be from database)
    print("\n📤 Test 2: First schema fetch (should be from database)")
    start_time = time.time()
    result1 = await fetch_schema_context()
    fetch_time_1 = time.time() - start_time
    
    print(f"✅ Status: {result1.get('status')}")
    print(f"   Cached: {result1.get('cached', False)}")
    print(f"   Fetch time: {fetch_time_1:.3f}s")
    if result1.get('status') == 'success':
        schema = result1.get('schema_context', {})
        print(f"   Tables: {len(schema.get('tables', {}))}")
        cache_key = schema.get('metadata', {}).get('cache_key', 'unknown')
        print(f"   Cache key: {cache_key}")
    
    # Test 3: Second fetch (should be from cache if Redis available)
    print("\n📤 Test 3: Second schema fetch (should be from cache)")
    start_time = time.time()
    result2 = await fetch_schema_context()
    fetch_time_2 = time.time() - start_time
    
    print(f"✅ Status: {result2.get('status')}")
    print(f"   Cached: {result2.get('cached', False)}")
    print(f"   Fetch time: {fetch_time_2:.3f}s")
    print(f"   Speed improvement: {fetch_time_1/fetch_time_2:.1f}x faster" if fetch_time_2 > 0 else "")
    
    # Test 4: Cache info
    if redis_client.is_connected() and result1.get('status') == 'success':
        print("\n📤 Test 4: Cache information")
        schema = result1.get('schema_context', {})
        cache_key = schema.get('metadata', {}).get('cache_key', 'unknown')
        cache_info = redis_client.get_cache_info(cache_key)
        
        print(f"   Cache exists: {cache_info.get('exists')}")
        print(f"   TTL: {cache_info.get('ttl')} seconds")
        print(f"   Expires in: {cache_info.get('expires_in')}")
    
    # Test 5: Specific table caching
    print("\n📤 Test 5: Specific table caching")
    if result1.get('status') == 'success':
        schema = result1.get('schema_context', {})
        available_tables = list(schema.get('tables', {}).keys())
        
        if available_tables:
            test_table = available_tables[0]
            print(f"   Testing with table: {test_table}")
            
            # First fetch for specific table
            start_time = time.time()
            result3 = await fetch_schema_context(table_names=[test_table])
            fetch_time_3 = time.time() - start_time
            
            print(f"   First fetch time: {fetch_time_3:.3f}s")
            print(f"   Cached: {result3.get('cached', False)}")
            
            # Second fetch for same table (should be cached)
            start_time = time.time()
            result4 = await fetch_schema_context(table_names=[test_table])
            fetch_time_4 = time.time() - start_time
            
            print(f"   Second fetch time: {fetch_time_4:.3f}s")
            print(f"   Cached: {result4.get('cached', False)}")
            print(f"   Speed improvement: {fetch_time_3/fetch_time_4:.1f}x faster" if fetch_time_4 > 0 else "")
    
    # Test 6: Cache invalidation
    if redis_client.is_connected():
        print("\n📤 Test 6: Cache invalidation")
        cache_key = "schema:all_tables"  # Default cache key for all tables
        
        # Check if cache exists
        cache_info_before = redis_client.get_cache_info(cache_key)
        print(f"   Cache exists before invalidation: {cache_info_before.get('exists')}")
        
        # Invalidate cache
        invalidated = redis_client.invalidate_schema_cache(cache_key)
        print(f"   Cache invalidated: {invalidated}")
        
        # Check if cache exists after invalidation
        cache_info_after = redis_client.get_cache_info(cache_key)
        print(f"   Cache exists after invalidation: {cache_info_after.get('exists')}")
        
        # Fetch again (should be from database)
        start_time = time.time()
        result5 = await fetch_schema_context()
        fetch_time_5 = time.time() - start_time
        
        print(f"   Fetch after invalidation time: {fetch_time_5:.3f}s")
        print(f"   Cached: {result5.get('cached', False)}")
    
    print("\n🎉 Redis caching test completed!")

if __name__ == "__main__":
    asyncio.run(test_redis_caching()) 