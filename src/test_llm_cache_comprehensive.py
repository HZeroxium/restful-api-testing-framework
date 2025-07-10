# test_llm_cache_comprehensive.py

"""Comprehensive test for LLM cache functionality."""

import asyncio
import time
from typing import Dict, Any
from pydantic import BaseModel, Field

from .utils.llm_utils import (
    create_and_execute_llm_agent,
    get_cache_debug_info,
    clear_llm_cache,
    _get_cache_instance,
    _generate_cache_key,
    CACHE_CONFIG,
)
from .common.logger import LoggerFactory, LoggerType, LogLevel

# Initialize logger
logger = LoggerFactory.get_logger(
    name="test.llm_cache_comprehensive",
    logger_type=LoggerType.STANDARD,
    level=LogLevel.DEBUG,
)


class LLMAnswer(BaseModel):
    """Model to represent the answer from an LLM agent."""

    answer: str = Field(..., description="The answer provided by the LLM agent")


async def test_cache_key_generation():
    """Test that cache keys are generated consistently."""
    logger.info("Testing cache key generation consistency")

    # Test parameters
    app_name = "test_app"
    agent_name = "test_agent"
    instruction = "What is the capital of France?"
    input_data = {"country": "France"}

    # Generate cache key multiple times
    key1 = _generate_cache_key(app_name, agent_name, instruction, input_data)
    key2 = _generate_cache_key(app_name, agent_name, instruction, input_data)
    key3 = _generate_cache_key(app_name, agent_name, instruction, input_data)

    logger.debug(f"Generated keys: {key1}, {key2}, {key3}")

    # All keys should be identical
    assert key1 == key2 == key3, f"Cache keys are inconsistent: {key1}, {key2}, {key3}"
    logger.info("✓ Cache key generation is consistent")

    # Test with different inputs
    different_input = {"country": "Germany"}
    key4 = _generate_cache_key(app_name, agent_name, instruction, different_input)

    assert key1 != key4, "Different inputs should produce different cache keys"
    logger.info("✓ Different inputs produce different cache keys")

    return key1


async def test_cache_basic_operations():
    """Test basic cache operations."""
    logger.info("Testing basic cache operations")

    cache = _get_cache_instance()
    test_key = "test_basic_ops"
    test_value = {"test": "data", "number": 42}

    # Clear any existing test data
    cache.delete(test_key)

    # Test set and get
    success = cache.set(test_key, test_value, ttl=60)
    assert success, "Cache set operation failed"
    logger.debug("✓ Cache set operation successful")

    # Test get
    retrieved = cache.get(test_key)
    assert (
        retrieved == test_value
    ), f"Retrieved value doesn't match: {retrieved} != {test_value}"
    logger.debug("✓ Cache get operation successful")

    # Test exists
    exists = cache.exists(test_key)
    assert exists, "Cache exists check failed"
    logger.debug("✓ Cache exists check successful")

    # Test delete
    deleted = cache.delete(test_key)
    assert deleted, "Cache delete operation failed"
    logger.debug("✓ Cache delete operation successful")

    # Verify deletion
    exists_after = cache.exists(test_key)
    assert not exists_after, "Key still exists after deletion"
    logger.debug("✓ Key properly deleted")

    logger.info("✓ Basic cache operations working correctly")


async def test_llm_cache_end_to_end():
    """Test end-to-end LLM caching."""
    logger.info("Testing end-to-end LLM caching")

    # Clear any existing cache
    clear_llm_cache()

    # Test parameters
    app_name = "test_app"
    agent_name = "test_agent"
    instruction = 'What is the capital of France? Please respond with JSON format: {"answer": "city_name"}'
    input_data = {"country": "France"}

    # Generate expected cache key
    expected_cache_key = _generate_cache_key(
        app_name, agent_name, instruction, input_data
    )

    logger.debug(f"Expected cache key: {expected_cache_key}")

    # Get debug info before first call
    debug_before = get_cache_debug_info(expected_cache_key)
    logger.debug(f"Cache state before first call: {debug_before}")

    # First call - should miss cache and call LLM
    logger.info("Making first LLM call (should miss cache)")
    start_time = time.time()

    result1 = await create_and_execute_llm_agent(
        app_name=app_name,
        agent_name=agent_name,
        instruction=instruction,
        input_data=input_data,
        output_schema=LLMAnswer,
        verbose=True,
        cache_enabled=True,
    )

    first_call_time = time.time() - start_time
    logger.info(f"First call completed in {first_call_time:.2f} seconds")
    logger.debug(f"First call result: {result1}")

    # Verify we got a result
    assert result1 is not None, "First LLM call should return a result"
    assert isinstance(result1, dict), "Result should be a dictionary"
    assert "answer" in result1, "Result should contain 'answer' key"

    # Get debug info after first call
    debug_after_first = get_cache_debug_info(expected_cache_key)
    logger.debug(f"Cache state after first call: {debug_after_first}")

    # Verify cache entry was created
    cache = _get_cache_instance()
    assert cache.exists(expected_cache_key), "Cache entry should exist after first call"
    logger.info("✓ Cache entry created after first call")

    # Wait a moment to ensure timing difference
    await asyncio.sleep(0.1)

    # Second call - should hit cache and be faster
    logger.info("Making second LLM call (should hit cache)")
    start_time = time.time()

    result2 = await create_and_execute_llm_agent(
        app_name=app_name,
        agent_name=agent_name,
        instruction=instruction,
        input_data=input_data,
        output_schema=LLMAnswer,
        verbose=True,
        cache_enabled=True,
    )

    second_call_time = time.time() - start_time
    logger.info(f"Second call completed in {second_call_time:.2f} seconds")
    logger.debug(f"Second call result: {result2}")

    # Verify results are identical
    assert (
        result1 == result2
    ), f"Cache hit should return identical result: {result1} != {result2}"
    logger.info("✓ Cache hit returned identical result")

    # Second call should be significantly faster (cache hit)
    # Allow some margin for network/system variations
    if second_call_time < first_call_time * 0.5:
        logger.info(
            f"✓ Cache hit was faster ({second_call_time:.2f}s vs {first_call_time:.2f}s)"
        )
    else:
        logger.warning(
            f"Cache hit timing unclear ({second_call_time:.2f}s vs {first_call_time:.2f}s)"
        )

    # Get debug info after second call
    debug_after_second = get_cache_debug_info(expected_cache_key)
    logger.debug(f"Cache state after second call: {debug_after_second}")

    # Test with cache disabled
    logger.info("Testing with cache disabled")
    start_time = time.time()

    result3 = await create_and_execute_llm_agent(
        app_name=app_name,
        agent_name=agent_name,
        instruction=instruction,
        input_data=input_data,
        output_schema=LLMAnswer,
        verbose=True,
        cache_enabled=False,
    )

    third_call_time = time.time() - start_time
    logger.info(
        f"Third call (cache disabled) completed in {third_call_time:.2f} seconds"
    )

    # Result should still be valid but took longer
    assert result3 is not None, "LLM call with cache disabled should return a result"
    logger.info("✓ LLM call works with cache disabled")

    # Clean up
    clear_llm_cache()
    logger.info("✓ Cache cleared after test")

    logger.info("✓ End-to-end LLM caching test completed successfully")

    return {
        "first_call_time": first_call_time,
        "second_call_time": second_call_time,
        "third_call_time": third_call_time,
        "cache_key": expected_cache_key,
        "results_identical": result1 == result2,
    }


async def test_cache_with_different_inputs():
    """Test cache behavior with different inputs."""
    logger.info("Testing cache with different inputs")

    clear_llm_cache()

    # Test with different countries
    countries = ["France", "Germany", "Italy"]
    results = {}

    for country in countries:
        logger.info(f"Testing with country: {country}")

        result = await create_and_execute_llm_agent(
            app_name="test_app",
            agent_name="test_agent",
            instruction=f'What is the capital of {country}? Please respond with JSON format: {{"answer": "city_name"}}',
            input_data={"country": country},
            verbose=True,
            cache_enabled=True,
        )

        results[country] = result
        logger.debug(f"Result for {country}: {result}")

    # Verify all results are different
    for i, country1 in enumerate(countries):
        for country2 in countries[i + 1 :]:
            assert (
                results[country1] != results[country2]
            ), f"Results for {country1} and {country2} should be different"

    logger.info("✓ Different inputs produce different cached results")

    # Test cache hits for same inputs
    logger.info("Testing cache hits for repeated inputs")

    for country in countries:
        logger.info(f"Re-testing with country: {country} (should hit cache)")

        result = await create_and_execute_llm_agent(
            app_name="test_app",
            agent_name="test_agent",
            instruction=f'What is the capital of {country}? Please respond with JSON format: {{"answer": "city_name"}}',
            input_data={"country": country},
            verbose=True,
            cache_enabled=True,
        )

        assert (
            result == results[country]
        ), f"Cache hit for {country} should return identical result"

    logger.info("✓ Cache hits work correctly for different inputs")

    clear_llm_cache()
    return results


async def main():
    """Run all cache tests."""
    logger.info("Starting comprehensive LLM cache tests")
    logger.info("=" * 60)

    try:
        # Test cache key generation
        await test_cache_key_generation()
        logger.info("")

        # Test basic cache operations
        await test_cache_basic_operations()
        logger.info("")

        # Test end-to-end caching
        e2e_results = await test_llm_cache_end_to_end()
        logger.info("")

        # Test with different inputs
        await test_cache_with_different_inputs()
        logger.info("")

        # Print summary
        logger.info("=" * 60)
        logger.info("🎉 ALL CACHE TESTS PASSED SUCCESSFULLY!")
        logger.info("=" * 60)

        # Print performance summary
        logger.info("Performance Summary:")
        logger.info(f"  First call (cache miss): {e2e_results['first_call_time']:.2f}s")
        logger.info(
            f"  Second call (cache hit): {e2e_results['second_call_time']:.2f}s"
        )
        logger.info(
            f"  Third call (cache disabled): {e2e_results['third_call_time']:.2f}s"
        )
        logger.info(
            f"  Cache speedup: {e2e_results['first_call_time'] / e2e_results['second_call_time']:.1f}x"
        )

        return True

    except Exception as e:
        logger.error(f"❌ Cache test failed: {e}")
        logger.error("Stack trace:", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n🎉 All cache tests passed!")
    else:
        print("\n❌ Some cache tests failed!")
        exit(1)
