import json
import hashlib
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
import redis
import pickle
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Centralized cache management"""
    
    def __init__(self, redis_url=None):
        try:
            if redis_url:
                self.redis_client = redis.from_url(redis_url)
            else:
                # Default to local Redis instance
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
            
            # Test connection
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache initialized successfully")
            
        except (redis.ConnectionError, redis.RedisError) as e:
            logger.warning(f"Redis not available, using in-memory cache: {str(e)}")
            self.cache_enabled = False
            self.memory_cache = {}
            self.cache_timestamps = {}
    
    def _generate_cache_key(self, prefix, *args, **kwargs):
        """Generate a unique cache key"""
        key_data = f"{prefix}:{':'.join(map(str, args))}"
        if kwargs:
            key_data += f":{json.dumps(kwargs, sort_keys=True)}"
        
        # Hash the key to ensure consistent length and valid characters
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key):
        """Get value from cache"""
        try:
            if self.cache_enabled:
                data = self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
            else:
                # Use in-memory cache
                if key in self.memory_cache:
                    timestamp = self.cache_timestamps.get(key)
                    if timestamp and datetime.now() - timestamp < timedelta(minutes=30):
                        return self.memory_cache[key]
                    else:
                        # Expired, remove from cache
                        del self.memory_cache[key]
                        if key in self.cache_timestamps:
                            del self.cache_timestamps[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, key, value, ttl=3600):
        """Set value in cache with TTL (time to live) in seconds"""
        try:
            if self.cache_enabled:
                serialized_data = pickle.dumps(value)
                self.redis_client.setex(key, ttl, serialized_data)
            else:
                # Use in-memory cache
                self.memory_cache[key] = value
                self.cache_timestamps[key] = datetime.now()
                
                # Clean up old entries (keep only last 1000 items)
                if len(self.memory_cache) > 1000:
                    oldest_keys = sorted(
                        self.cache_timestamps.keys(),
                        key=lambda k: self.cache_timestamps[k]
                    )[:100]
                    
                    for old_key in oldest_keys:
                        del self.memory_cache[old_key]
                        del self.cache_timestamps[old_key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    def delete(self, key):
        """Delete value from cache"""
        try:
            if self.cache_enabled:
                self.redis_client.delete(key)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    def clear_pattern(self, pattern):
        """Clear all keys matching a pattern"""
        try:
            if self.cache_enabled:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # For in-memory cache, we'll need to iterate through keys
                keys_to_delete = [key for key in self.memory_cache.keys() if pattern in key]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    if key in self.cache_timestamps:
                        del self.cache_timestamps[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return False
    
    def get_stats(self):
        """Get cache statistics"""
        try:
            if self.cache_enabled:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', 'Unknown'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            else:
                return {
                    'type': 'memory',
                    'cached_items': len(self.memory_cache),
                    'memory_usage': 'Unknown'
                }
                
        except Exception as e:
            logger.error(f"Cache stats error: {str(e)}")
            return {'type': 'error', 'error': str(e)}

# Initialize cache manager
cache_manager = CacheManager()

# Caching decorators
def cache_response(ttl=3600, key_prefix='api'):
    """Decorator to cache API responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key based on endpoint, args, and query parameters
            cache_key = cache_manager._generate_cache_key(
                key_prefix,
                request.endpoint,
                request.method,
                *args,
                **dict(request.args)
            )
            
            # Try to get from cache
            cached_response = cache_manager.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_response
            
            # Execute function and cache result
            logger.debug(f"Cache miss for key: {cache_key}")
            result = f(*args, **kwargs)
            
            # Only cache successful responses
            if isinstance(result, tuple):
                response_data, status_code = result
                if status_code == 200:
                    cache_manager.set(cache_key, result, ttl)
            elif hasattr(result, 'status_code') and result.status_code == 200:
                cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return decorated_function
    return decorator

def cache_function_result(ttl=3600, key_prefix='func'):
    """Decorator to cache function results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_cache_key(
                key_prefix,
                f.__name__,
                *args,
                **kwargs
            )
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return decorated_function
    return decorator

def invalidate_cache_on_change(cache_patterns):
    """Decorator to invalidate cache when data changes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Invalidate cache patterns after successful operation
            if isinstance(result, tuple):
                _, status_code = result
                if status_code in [200, 201, 204]:
                    for pattern in cache_patterns:
                        cache_manager.clear_pattern(pattern)
            elif hasattr(result, 'status_code') and result.status_code in [200, 201, 204]:
                for pattern in cache_patterns:
                    cache_manager.clear_pattern(pattern)
            
            return result
        
        return decorated_function
    return decorator

class ItemCache:
    """Specialized caching for items"""
    
    @staticmethod
    def get_featured_items():
        """Get cached featured items"""
        return cache_manager.get('featured_items')
    
    @staticmethod
    def set_featured_items(items, ttl=1800):  # 30 minutes
        """Cache featured items"""
        return cache_manager.set('featured_items', items, ttl)
    
    @staticmethod
    def get_category_items(category_id, page=1, limit=20):
        """Get cached category items"""
        cache_key = f"category_items:{category_id}:{page}:{limit}"
        return cache_manager.get(cache_key)
    
    @staticmethod
    def set_category_items(category_id, page, limit, items, ttl=900):  # 15 minutes
        """Cache category items"""
        cache_key = f"category_items:{category_id}:{page}:{limit}"
        return cache_manager.set(cache_key, items, ttl)
    
    @staticmethod
    def invalidate_item_caches(item_id=None):
        """Invalidate item-related caches"""
        patterns = ['featured_items', 'category_items:*', 'search_results:*']
        if item_id:
            patterns.append(f'item:{item_id}:*')
        
        for pattern in patterns:
            cache_manager.clear_pattern(pattern)

class UserCache:
    """Specialized caching for users"""
    
    @staticmethod
    def get_user_profile(user_id):
        """Get cached user profile"""
        cache_key = f"user_profile:{user_id}"
        return cache_manager.get(cache_key)
    
    @staticmethod
    def set_user_profile(user_id, profile, ttl=3600):  # 1 hour
        """Cache user profile"""
        cache_key = f"user_profile:{user_id}"
        return cache_manager.set(cache_key, profile, ttl)
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """Invalidate user-related caches"""
        patterns = [f'user_profile:{user_id}', f'user_items:{user_id}:*']
        for pattern in patterns:
            cache_manager.clear_pattern(pattern)

class SearchCache:
    """Specialized caching for search results"""
    
    @staticmethod
    def get_search_results(query, filters=None, page=1, limit=20):
        """Get cached search results"""
        cache_key = cache_manager._generate_cache_key(
            'search_results',
            query,
            page,
            limit,
            **(filters or {})
        )
        return cache_manager.get(cache_key)
    
    @staticmethod
    def set_search_results(query, filters, page, limit, results, ttl=600):  # 10 minutes
        """Cache search results"""
        cache_key = cache_manager._generate_cache_key(
            'search_results',
            query,
            page,
            limit,
            **(filters or {})
        )
        return cache_manager.set(cache_key, results, ttl)
    
    @staticmethod
    def invalidate_search_cache():
        """Invalidate all search caches"""
        cache_manager.clear_pattern('search_results:*')

# Cache warming functions
def warm_cache():
    """Warm up the cache with frequently accessed data"""
    try:
        logger.info("Starting cache warming...")
        
        # Warm up featured items
        # In a real app, you'd fetch this from the database
        featured_items = []  # Fetch from database
        ItemCache.set_featured_items(featured_items)
        
        # Warm up popular categories
        # In a real app, you'd fetch popular categories and their items
        
        logger.info("Cache warming completed")
        
    except Exception as e:
        logger.error(f"Cache warming error: {str(e)}")

def init_caching(app):
    """Initialize caching for the Flask app"""
    
    @app.route('/api/cache/stats', methods=['GET'])
    def get_cache_stats():
        """Endpoint to get cache statistics"""
        try:
            stats = cache_manager.get_stats()
            return jsonify({
                'success': True,
                'data': stats
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cache/clear', methods=['POST'])
    def clear_cache():
        """Endpoint to clear cache (admin only)"""
        try:
            # In a real app, you'd check admin permissions here
            cache_manager.clear_pattern('*')
            
            return jsonify({
                'success': True,
                'message': 'Cache cleared successfully'
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Warm cache on startup
    warm_cache()

