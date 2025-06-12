"""
Comprehensive demonstration of the extensible caching system
"""

import time
import random
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

# Import cache components
from common.cache import (
    CacheType,
    CacheFactory,
    cache_result,
    cache_property,
    cached_method,
)

# Import logger for output (instead of print)
from common.logger import LoggerFactory, LoggerType, LogLevel

# Create demo logger
logger = LoggerFactory.get_logger(
    name="cache-demo",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.INFO,
    use_colors=True,
)

# Try to import Redis cache (optional)
try:
    from common.cache import RedisCache

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - Redis demos will be skipped")


@dataclass
class APIResponse:
    """Sample data structure for caching demos"""

    status_code: int
    data: Dict[str, Any]
    headers: Dict[str, str]
    response_time: float


def demo_basic_cache_operations():
    """Demonstrate basic cache operations"""
    logger.info("=" * 80)
    logger.info("🎯 DEMO 1: Basic Cache Operations")
    logger.info("=" * 80)

    # Create in-memory cache
    cache = CacheFactory.create_memory_cache(max_size=100)

    logger.info("📝 Testing basic set/get operations:")

    # Basic operations
    cache.set("user:123", {"name": "John Doe", "email": "john@example.com"})
    cache.set("config:timeout", 30)
    cache.set("api:key", "abc123def456")

    user_data = cache.get("user:123")
    timeout = cache.get("config:timeout")
    api_key = cache.get("api:key")

    logger.info(f"   Retrieved user data: {user_data}")
    logger.info(f"   Retrieved timeout: {timeout}")
    logger.info(f"   Retrieved API key: {api_key}")

    logger.info("📝 Testing default values:")
    missing_value = cache.get("nonexistent:key", "default_value")
    logger.info(f"   Missing key with default: {missing_value}")

    logger.info("📝 Testing existence checks:")
    logger.info(f"   user:123 exists: {cache.exists('user:123')}")
    logger.info(f"   missing:key exists: {cache.exists('missing:key')}")

    logger.info("📝 Testing key listing:")
    keys = cache.keys()
    logger.info(f"   All keys: {keys}")

    # Cache statistics
    stats = cache.get_stats()
    logger.info(
        f"📊 Cache stats - Hits: {stats.hits}, Misses: {stats.misses}, Sets: {stats.sets}"
    )


def demo_ttl_functionality():
    """Demonstrate TTL (Time To Live) functionality"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 2: TTL (Time To Live) Functionality")
    logger.info("=" * 80)

    cache = CacheFactory.create_memory_cache()

    logger.info("📝 Setting values with different TTL:")

    # Set values with TTL
    cache.set("short_lived", "expires in 2 seconds", ttl=2)
    cache.set("medium_lived", "expires in 5 seconds", ttl=5)
    cache.set("long_lived", "expires in 10 seconds", ttl=10)
    cache.set("permanent", "never expires")  # No TTL

    logger.info("   Set values with TTL: 2s, 5s, 10s, and permanent")

    # Check initial TTL values
    logger.info("📝 Initial TTL values:")
    logger.info(f"   short_lived TTL: {cache.get_ttl('short_lived')}s")
    logger.info(f"   medium_lived TTL: {cache.get_ttl('medium_lived')}s")
    logger.info(f"   permanent TTL: {cache.get_ttl('permanent')}")

    # Wait and check expiration
    logger.info("📝 Waiting 3 seconds...")
    time.sleep(3)

    logger.info("📝 After 3 seconds:")
    logger.info(f"   short_lived exists: {cache.exists('short_lived')}")
    logger.info(f"   medium_lived exists: {cache.exists('medium_lived')}")
    logger.info(f"   medium_lived TTL: {cache.get_ttl('medium_lived')}s")

    # Modify TTL of existing key
    logger.info("📝 Extending medium_lived TTL to 10 seconds:")
    cache.set_ttl("medium_lived", 10)
    logger.info(f"   medium_lived new TTL: {cache.get_ttl('medium_lived')}s")


def demo_different_cache_types():
    """Demonstrate different cache implementations"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 3: Different Cache Implementations")
    logger.info("=" * 80)

    # In-Memory Cache
    logger.info("📝 In-Memory Cache:")
    memory_cache = CacheFactory.create_memory_cache(max_size=50, enable_lru=True)
    memory_cache.set("memory:test", {"type": "in-memory", "fast": True})

    result = memory_cache.get("memory:test")
    memory_usage = memory_cache.get_memory_usage()
    logger.info(f"   Stored and retrieved: {result}")
    logger.info(
        f"   Memory usage: {memory_usage['total_mb']:.2f} MB, {memory_usage['entry_count']} entries"
    )

    # File Cache
    logger.info("📝 File Cache:")
    cache_dir = Path("demo_cache")
    file_cache = CacheFactory.create_file_cache(
        cache_dir=str(cache_dir), serialization="json", create_subdirs=True
    )

    file_cache.set("file:test", {"type": "file-based", "persistent": True})
    result = file_cache.get("file:test")
    file_usage = file_cache.get_memory_usage()
    logger.info(f"   Stored and retrieved: {result}")
    logger.info(
        f"   File usage: {file_usage['total_mb']:.2f} MB, {file_usage['file_count']} files"
    )
    logger.info(f"   Cache directory: {file_usage['cache_dir']}")

    # Redis Cache (if available)
    if REDIS_AVAILABLE:
        logger.info("📝 Redis Cache:")
        try:
            redis_cache = CacheFactory.create_redis_cache(
                host="localhost",
                port=6379,
                db=1,  # Use different DB for demo
                key_prefix="demo:",
            )

            # Test connection
            if redis_cache.ping():
                redis_cache.set("redis:test", {"type": "redis", "distributed": True})
                result = redis_cache.get("redis:test")
                redis_info = redis_cache.get_memory_usage()
                logger.info(f"   Stored and retrieved: {result}")
                logger.info(
                    f"   Redis memory: {redis_info.get('used_memory_human', 'N/A')}"
                )
            else:
                logger.warning("   Redis connection failed - skipping Redis demo")

        except Exception as e:
            logger.warning(f"   Redis demo failed: {e}")
    else:
        logger.info("📝 Redis Cache: Not available (install redis-py)")


def demo_cache_factory():
    """Demonstrate cache factory pattern"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 4: Cache Factory Pattern")
    logger.info("=" * 80)

    logger.info("📝 Getting cached instances (same instance returned):")

    # Get same cache instance multiple times
    cache1 = CacheFactory.get_cache("api-cache", CacheType.MEMORY)
    cache2 = CacheFactory.get_cache("api-cache", CacheType.MEMORY)

    logger.info(f"   Cache instances are same: {cache1 is cache2}")

    # Set value in cache1, retrieve from cache2
    cache1.set("shared:data", "This is shared!")
    shared_data = cache2.get("shared:data")
    logger.info(f"   Shared data: {shared_data}")

    logger.info("📝 Creating different cache types:")

    memory_cache = CacheFactory.get_cache("memory-cache", CacheType.MEMORY)
    file_cache = CacheFactory.get_cache("file-cache", CacheType.FILE)

    memory_cache.set("cache:type", "memory")
    file_cache.set("cache:type", "file")

    logger.info(f"   Memory cache type: {memory_cache.get('cache:type')}")
    logger.info(f"   File cache type: {file_cache.get('cache:type')}")

    # Show factory info
    factory_info = CacheFactory.get_cache_instance_info()
    logger.info(f"📊 Factory instances: {factory_info}")


def demo_cache_decorators():
    """Demonstrate cache decorators"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 5: Cache Decorators")
    logger.info("=" * 80)

    # Function caching
    @cache_result(ttl=5, cache_type=CacheType.MEMORY, cache_name="function_cache")
    def expensive_calculation(n: int) -> int:
        """Simulate expensive computation"""
        logger.info(f"   🔄 Computing factorial of {n} (expensive operation)")
        time.sleep(0.1)  # Simulate work
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result

    logger.info("📝 Function caching with @cache_result:")

    # First call - should compute
    start_time = time.time()
    result1 = expensive_calculation(10)
    time1 = time.time() - start_time
    logger.info(f"   First call result: {result1} (took {time1:.3f}s)")

    # Second call - should use cache
    start_time = time.time()
    result2 = expensive_calculation(10)
    time2 = time.time() - start_time
    logger.info(f"   Second call result: {result2} (took {time2:.3f}s)")

    logger.info(f"   Speed improvement: {time1/time2:.1f}x faster!")

    # Cache info
    cache_info = expensive_calculation.get_cache_info()
    logger.info(f"   Cache info: {cache_info['cached_entries']} entries")

    # Property caching
    class APIClient:
        @cache_property(ttl=3, cache_type=CacheType.MEMORY)
        def server_info(self) -> Dict[str, Any]:
            """Simulate API call to get server info"""
            logger.info("   🌐 Fetching server info (API call)")
            time.sleep(0.05)  # Simulate network delay
            return {
                "version": "1.2.3",
                "uptime": f"{random.randint(1000, 9999)}s",
                "load": random.uniform(0.1, 0.9),
            }

        @cached_method(ttl=2, cache_type=CacheType.MEMORY)
        def get_user_data(self, user_id: int) -> Dict[str, Any]:
            """Simulate API call to get user data"""
            logger.info(f"   👤 Fetching user data for ID {user_id} (API call)")
            time.sleep(0.05)  # Simulate network delay
            return {
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com",
            }

    logger.info("📝 Property and method caching:")

    client = APIClient()

    # Property caching
    logger.info("   Testing cached property:")
    info1 = client.server_info  # Should fetch
    info2 = client.server_info  # Should use cache
    logger.info(f"   Server info consistent: {info1 == info2}")

    # Method caching
    logger.info("   Testing cached method:")
    user1 = client.get_user_data(123)  # Should fetch
    user2 = client.get_user_data(123)  # Should use cache
    user3 = client.get_user_data(456)  # Should fetch (different args)

    logger.info(f"   User 123 consistent: {user1 == user2}")
    logger.info(f"   Different users: {user1['id'] != user3['id']}")


def demo_lru_eviction():
    """Demonstrate LRU eviction policy"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 6: LRU Eviction Policy")
    logger.info("=" * 80)

    # Create cache with small max size
    cache = CacheFactory.create_memory_cache(max_size=3, enable_lru=True)

    logger.info("📝 Creating cache with max_size=3 and LRU enabled:")

    # Fill cache to capacity
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")

    keys = cache.keys()
    logger.info(f"   Cache full with keys: {keys}")

    # Access key1 to make it recently used
    logger.info("📝 Accessing key1 to make it recently used:")
    cache.get("key1")

    # Add new key - should evict least recently used (key2)
    logger.info("📝 Adding key4 (should evict key2 - least recently used):")
    cache.set("key4", "value4")

    remaining_keys = cache.keys()
    logger.info(f"   Remaining keys: {remaining_keys}")
    logger.info(f"   key2 evicted: {'key2' not in remaining_keys}")
    logger.info(f"   key1 preserved: {'key1' in remaining_keys}")


def demo_performance_comparison():
    """Compare performance of different cache implementations"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 7: Performance Comparison")
    logger.info("=" * 80)

    test_data = {"key": f"value_{i}" for i in range(100)}
    iterations = 1000

    logger.info(f"📝 Performance test with {iterations} operations:")

    # Test In-Memory Cache
    memory_cache = CacheFactory.create_memory_cache()

    start_time = time.time()
    for i in range(iterations):
        key = f"perf:memory:{i % 100}"
        if i < 100:
            memory_cache.set(key, test_data)
        else:
            memory_cache.get(key)
    memory_time = time.time() - start_time

    # Test File Cache
    file_cache = CacheFactory.create_file_cache(cache_dir="perf_test_cache")

    start_time = time.time()
    for i in range(iterations):
        key = f"perf:file:{i % 100}"
        if i < 100:
            file_cache.set(key, test_data)
        else:
            file_cache.get(key)
    file_time = time.time() - start_time

    logger.info("📊 Performance Results:")
    logger.info(f"   Memory Cache: {memory_time:.3f} seconds")
    logger.info(f"   File Cache: {file_time:.3f} seconds")
    logger.info(f"   Memory is {file_time/memory_time:.1f}x faster than File")

    # Get memory usage info
    memory_usage = memory_cache.get_memory_usage()
    file_usage = file_cache.get_memory_usage()

    logger.info("📊 Resource Usage:")
    logger.info(f"   Memory Cache: {memory_usage['total_mb']:.2f} MB in memory")
    logger.info(f"   File Cache: {file_usage['total_mb']:.2f} MB on disk")


def demo_api_testing_scenario():
    """Demonstrate realistic API testing caching scenario"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 8: API Testing Scenario")
    logger.info("=" * 80)

    # Create cache for API responses
    api_cache = CacheFactory.get_cache(
        name="api-response-cache",
        cache_type=CacheType.MEMORY,
        max_size=200,
        default_ttl=300,  # 5 minutes default TTL
    )

    logger.info("📝 Simulating API testing framework with caching:")

    def simulate_api_call(
        endpoint: str, method: str = "GET", cache_ttl: int = 60
    ) -> APIResponse:
        """Simulate API call with caching"""
        cache_key = f"api:{method}:{endpoint}"

        # Check cache first
        cached_response = api_cache.get(cache_key)
        if cached_response:
            logger.info(f"   ⚡ Cache HIT for {method} {endpoint}")
            return APIResponse(**cached_response)

        # Simulate API call
        logger.info(f"   🌐 Cache MISS - Making real API call to {method} {endpoint}")
        time.sleep(random.uniform(0.1, 0.5))  # Simulate network delay

        # Create mock response
        response = APIResponse(
            status_code=200,
            data={"endpoint": endpoint, "timestamp": time.time()},
            headers={"Content-Type": "application/json"},
            response_time=random.uniform(50, 300),
        )

        # Cache the response
        api_cache.set(cache_key, response.__dict__, ttl=cache_ttl)
        logger.info(f"   💾 Cached response for {cache_ttl}s")

        return response

    # Test API caching scenario
    endpoints = [
        "/api/v1/users",
        "/api/v1/users/123",
        "/api/v1/posts",
        "/api/v1/users",  # Repeat to show cache hit
        "/api/v1/users/123",  # Repeat to show cache hit
    ]

    logger.info("📝 Making API calls:")
    for endpoint in endpoints:
        response = simulate_api_call(endpoint, cache_ttl=30)
        logger.info(
            f"   📊 {endpoint}: {response.status_code} ({response.response_time:.1f}ms)"
        )

    # Show cache statistics
    stats = api_cache.get_stats()
    hit_rate = stats.get_hit_rate() * 100
    logger.info(f"📊 Cache Performance:")
    logger.info(f"   Hit Rate: {hit_rate:.1f}%")
    logger.info(f"   Total Hits: {stats.hits}")
    logger.info(f"   Total Misses: {stats.misses}")
    logger.info(f"   Cache Size: {api_cache.get_size()} entries")


def demo_cache_invalidation():
    """Demonstrate cache invalidation strategies"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 9: Cache Invalidation Strategies")
    logger.info("=" * 80)

    cache = CacheFactory.create_memory_cache()

    logger.info("📝 Setting up test data:")

    # Set up test data
    cache.set("user:1", {"name": "Alice", "email": "alice@example.com"})
    cache.set("user:2", {"name": "Bob", "email": "bob@example.com"})
    cache.set("config:app", {"theme": "dark", "timeout": 30})
    cache.set("config:db", {"host": "localhost", "port": 5432})
    cache.set("temp:session", {"id": "abc123", "expires": time.time() + 3600})

    initial_keys = cache.keys()
    logger.info(f"   Initial keys: {initial_keys}")

    logger.info("📝 Selective invalidation by pattern:")

    # Invalidate user data
    user_keys = [key for key in cache.keys() if key.startswith("user:")]
    for key in user_keys:
        cache.delete(key)

    remaining_keys = cache.keys()
    logger.info(f"   After user invalidation: {remaining_keys}")

    logger.info("📝 Bulk invalidation:")

    # Add more data
    for i in range(5):
        cache.set(f"temp:bulk:{i}", f"data_{i}")

    logger.info(f"   Added bulk data: {[k for k in cache.keys() if 'bulk' in k]}")

    # Clear all temp data
    temp_keys = [key for key in cache.keys() if key.startswith("temp:")]
    for key in temp_keys:
        cache.delete(key)

    final_keys = cache.keys()
    logger.info(f"   After temp invalidation: {final_keys}")

    logger.info("📝 Complete cache clear:")
    cache.clear()
    logger.info(f"   After clear: {cache.keys()}")


def demo_cache_serialization():
    """Demonstrate different serialization methods"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 10: Cache Serialization Methods")
    logger.info("=" * 80)

    # Complex data structures
    complex_data = {
        "users": [
            {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
            {"id": 2, "name": "Bob", "tags": ["user"]},
        ],
        "metadata": {
            "created": time.time(),
            "version": "1.0.0",
            "config": {"nested": {"deep": True}},
        },
    }

    logger.info("📝 Testing JSON serialization (File Cache):")

    json_cache = CacheFactory.create_file_cache(
        cache_dir="json_cache", serialization="json"
    )

    json_cache.set("complex:data", complex_data)
    retrieved_json = json_cache.get("complex:data")
    logger.info(f"   JSON serialization successful: {retrieved_json == complex_data}")

    logger.info("📝 Testing Pickle serialization (File Cache):")

    pickle_cache = CacheFactory.create_file_cache(
        cache_dir="pickle_cache", serialization="pickle"
    )

    # Pickle can handle more complex objects
    class CustomObject:
        def __init__(self, value):
            self.value = value

        def __eq__(self, other):
            return isinstance(other, CustomObject) and self.value == other.value

    custom_obj = CustomObject("test_value")
    pickle_cache.set("custom:object", custom_obj)
    retrieved_pickle = pickle_cache.get("custom:object")
    logger.info(f"   Pickle serialization successful: {retrieved_pickle == custom_obj}")
    logger.info(f"   Custom object value: {retrieved_pickle.value}")


def demo_error_handling():
    """Demonstrate error handling and resilience"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 11: Error Handling and Resilience")
    logger.info("=" * 80)

    cache = CacheFactory.create_memory_cache()

    logger.info("📝 Testing graceful error handling:")

    # Test with None values
    logger.info("   Setting None value:")
    success = cache.set("null:value", None)
    retrieved = cache.get("null:value", "default")
    logger.info(f"   None value handling: set={success}, get={retrieved}")

    # Test with large values
    logger.info("   Testing with large data:")
    large_data = {"data": "x" * 10000}  # 10KB string
    success = cache.set("large:data", large_data)
    logger.info(f"   Large data cached: {success}")

    # Test cache decorator error handling
    @cache_result(ttl=5, cache_type=CacheType.MEMORY)
    def potentially_failing_function(should_fail: bool = False):
        """Function that might raise exceptions"""
        if should_fail:
            raise ValueError("Simulated failure")
        return "success"

    logger.info("   Testing decorator with exceptions:")

    # Successful call
    try:
        result1 = potentially_failing_function(False)
        logger.info(f"   Successful call: {result1}")
    except Exception as e:
        logger.error(f"   Unexpected error: {e}")

    # Failing call
    try:
        result2 = potentially_failing_function(True)
        logger.info(f"   This shouldn't appear: {result2}")
    except ValueError as e:
        logger.info(f"   Exception handled correctly: {e}")

    # Verify cache still works after exception
    result3 = potentially_failing_function(False)
    logger.info(f"   Cache works after exception: {result3}")


def demo_monitoring_and_stats():
    """Demonstrate cache monitoring and statistics"""
    logger.info("\n" + "=" * 80)
    logger.info("🎯 DEMO 12: Monitoring and Statistics")
    logger.info("=" * 80)

    cache = CacheFactory.create_memory_cache(max_size=50)

    logger.info("📝 Generating cache activity for statistics:")

    # Generate some cache activity
    for i in range(20):
        cache.set(f"item:{i}", f"value_{i}")

    # Generate hits and misses
    for i in range(30):
        key = f"item:{i % 25}"  # Mix of existing and non-existing keys
        cache.get(key, "default")

    # Generate some deletes
    for i in range(5):
        cache.delete(f"item:{i}")

    # Get comprehensive statistics
    stats = cache.get_stats()
    memory_usage = cache.get_memory_usage()

    logger.info("📊 Cache Statistics:")
    logger.info(f"   Total Operations:")
    logger.info(f"     Sets: {stats.sets}")
    logger.info(f"     Gets: {stats.hits + stats.misses}")
    logger.info(f"     Hits: {stats.hits}")
    logger.info(f"     Misses: {stats.misses}")
    logger.info(f"     Deletes: {stats.deletes}")
    logger.info(f"   Performance:")
    logger.info(f"     Hit Rate: {stats.get_hit_rate():.2%}")
    logger.info(f"     Uptime: {stats.get_uptime():.1f}s")
    logger.info(f"   Memory Usage:")
    logger.info(f"     Total Size: {memory_usage['total_mb']:.2f} MB")
    logger.info(f"     Entry Count: {memory_usage['entry_count']}")
    logger.info(f"     Utilization: {memory_usage['utilization']:.2%}")
    logger.info(f"     Max Size: {memory_usage['max_size']}")


def cleanup_demo_files():
    """Clean up files created during demos"""
    logger.info("\n📁 Cleaning up demo files...")

    import shutil

    # Remove cache directories created during demos
    cache_dirs = ["demo_cache", "json_cache", "pickle_cache", "perf_test_cache"]

    for cache_dir in cache_dirs:
        path = Path(cache_dir)
        if path.exists():
            try:
                shutil.rmtree(path)
                logger.info(f"   Removed {cache_dir}")
            except Exception as e:
                logger.warning(f"   Failed to remove {cache_dir}: {e}")


def main():
    """Run all cache demos"""
    logger.info("🎉 Welcome to the Extensible Caching System Demo!")
    logger.info("This demo showcases the capabilities of our caching framework.")

    try:
        # Run all demos
        demo_basic_cache_operations()
        demo_ttl_functionality()
        demo_different_cache_types()
        demo_cache_factory()
        demo_cache_decorators()
        demo_lru_eviction()
        demo_performance_comparison()
        demo_api_testing_scenario()
        demo_cache_invalidation()
        demo_cache_serialization()
        demo_error_handling()
        demo_monitoring_and_stats()

        logger.info("\n" + "=" * 80)
        logger.info("🎊 Demo completed! The caching system is ready for use.")
        logger.info("=" * 80)

        logger.info("\n💡 Quick Usage Examples:")
        logger.info("   # Get a memory cache")
        logger.info("   from common.cache import CacheFactory, CacheType")
        logger.info("   cache = CacheFactory.get_cache('my-cache', CacheType.MEMORY)")
        logger.info("   ")
        logger.info("   # Use cache decorators")
        logger.info("   from common.cache import cache_result")
        logger.info("   @cache_result(ttl=300)  # 5 minutes")
        logger.info("   def expensive_function():")
        logger.info("       return compute_expensive_result()")
        logger.info("   ")
        logger.info("   # Different cache types")
        logger.info("   memory_cache = CacheFactory.get_cache('mem', CacheType.MEMORY)")
        logger.info("   file_cache = CacheFactory.get_cache('file', CacheType.FILE)")
        if REDIS_AVAILABLE:
            logger.info(
                "   redis_cache = CacheFactory.get_cache('redis', CacheType.REDIS)"
            )

    finally:
        # Always clean up
        cleanup_demo_files()


if __name__ == "__main__":
    main()
