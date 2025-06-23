"""
PostgreSQL AI Agent MVP - Redis Client Utility
"""

import redis
import json
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class RedisClient:
    """Utility class for Redis operations"""
    
    def __init__(self):
        """Initialize Redis client"""
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            # Create Redis connection
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis client initialized successfully")
            self.connected = True
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
            self.redis_client = None
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.connected
    
    def get_cached_schema(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached schema from Redis
        
        Args:
            cache_key: Key to identify the cached schema
            
        Returns:
            Cached schema data or None if not found/expired
        """
        if not self.connected:
            return None
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Schema cache hit for key: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"Schema cache miss for key: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error getting cached schema: {e}")
            return None
    
    def cache_schema(self, cache_key: str, schema_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """
        Cache schema data in Redis with TTL
        
        Args:
            cache_key: Key to identify the cached schema
            schema_data: Schema data to cache
            ttl_seconds: Time to live in seconds (default 1 hour)
            
        Returns:
            True if cached successfully, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            # Serialize data to JSON
            json_data = json.dumps(schema_data, default=str)
            
            # Set with TTL (1 hour default)
            result = self.redis_client.setex(cache_key, ttl_seconds, json_data)
            
            if result:
                logger.info(f"Schema cached successfully for key: {cache_key} (TTL: {ttl_seconds}s)")
                return True
            else:
                logger.warning(f"Failed to cache schema for key: {cache_key}")
                return False
                
        except Exception as e:
            logger.error(f"Error caching schema: {e}")
            return False
    
    def invalidate_schema_cache(self, cache_key: str) -> bool:
        """
        Invalidate (delete) cached schema
        
        Args:
            cache_key: Key to identify the cached schema
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            result = self.redis_client.delete(cache_key)
            if result:
                logger.info(f"Schema cache invalidated for key: {cache_key}")
                return True
            else:
                logger.info(f"No cache found to invalidate for key: {cache_key}")
                return False
        except Exception as e:
            logger.error(f"Error invalidating schema cache: {e}")
            return False
    
    def get_cache_info(self, cache_key: str) -> Dict[str, Any]:
        """
        Get cache information (TTL, existence)
        
        Args:
            cache_key: Key to check
            
        Returns:
            Dictionary with cache information
        """
        if not self.connected:
            return {"connected": False, "exists": False, "ttl": -1}
        
        try:
            exists = self.redis_client.exists(cache_key)
            ttl = self.redis_client.ttl(cache_key) if exists else -1
            
            return {
                "connected": True,
                "exists": bool(exists),
                "ttl": ttl,
                "expires_in": f"{ttl // 60}m {ttl % 60}s" if ttl > 0 else "expired/no_expiry"
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {"connected": False, "exists": False, "ttl": -1, "error": str(e)}
    
    def generate_schema_cache_key(self, table_names: Optional[list] = None, include_samples: bool = False) -> str:
        """
        Generate a cache key for schema data
        
        Args:
            table_names: List of table names (None for all tables)
            include_samples: Whether samples are included
            
        Returns:
            Cache key string
        """
        if table_names:
            tables_str = "_".join(sorted(table_names))
            key = f"schema:{tables_str}"
        else:
            key = "schema:all_tables"
        
        if include_samples:
            key += ":with_samples"
        
        return key

# Global instance
redis_client = None

def get_redis_client() -> RedisClient:
    """Get or create global Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
    return redis_client 