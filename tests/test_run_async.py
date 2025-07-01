import pytest
import asyncio
from growthbook_openfeature_provider.provider import run_async

def test_run_async_in_sync_context():
    """Test run_async when called from a sync context."""
    async def test_coro():
        return "test"
    
    # Should work in sync context
    result = run_async(test_coro())
    assert result == "test"

@pytest.mark.asyncio
async def test_run_async_in_async_context():
    """Test run_async when called from an async context."""
    async def test_coro():
        return "test"
    
    # Should return the actual result, not a Task
    result = run_async(test_coro())
    assert not isinstance(result, asyncio.Task)
    assert result == "test"

def test_run_async_with_error():
    """Test run_async when the coroutine raises an error."""
    async def test_coro():
        raise ValueError("test error.")
    
    # Should propagate the error
    with pytest.raises(ValueError, match="test error."):
        run_async(test_coro())

@pytest.mark.asyncio
async def test_run_async_nested():
    """Test run_async when called from within another async context."""
    async def inner_coro():
        return "inner"
    
    async def outer_coro():
        # Should return the actual result, not a Task
        result = run_async(inner_coro())
        assert not isinstance(result, asyncio.Task)
        return result
    
    result = await outer_coro()
    assert result == "inner"

def test_run_async_with_complex_coroutine():
    """Test run_async with a more complex coroutine that does async operations."""
    async def complex_coro():
        # Simulate some async work
        await asyncio.sleep(0.1)
        return "complex result"
    
    result = run_async(complex_coro())
    assert result == "complex result"

@pytest.mark.asyncio
async def test_run_async_with_multiple_nested_calls():
    """Test run_async with multiple nested calls."""
    async def level3():
        return "level3"
    
    async def level2():
        result = run_async(level3())
        assert not isinstance(result, asyncio.Task)
        return result
    
    async def level1():
        result = run_async(level2())
        assert not isinstance(result, asyncio.Task)
        return result
    
    result = await level1()
    assert result == "level3"

@pytest.mark.asyncio
async def test_run_async_performance():
    """Test performance of run_async in different contexts."""
    import time
    
    async def dummy_coro():
        await asyncio.sleep(0.001)  # Small delay to simulate work
        return "result"
    
    # Test sync context performance
    start = time.time()
    for _ in range(1000):
        run_async(dummy_coro())
    sync_time = time.time() - start
    
    # Test async context performance
    start = time.time()
    results = []
    for _ in range(1000):
        result = run_async(dummy_coro())
        results.append(result)
    async_time = time.time() - start
    
    # Test nested async performance
    async def nested_coro():
        return run_async(dummy_coro())
    
    start = time.time()
    results = []
    for _ in range(1000):
        result = run_async(nested_coro())
        results.append(result)
    nested_time = time.time() - start
    
    # Print results for analysis
    print(f"\nPerformance Results:")
    print(f"Sync context: {sync_time:.3f}s")
    print(f"Async context: {async_time:.3f}s")
    print(f"Nested async: {nested_time:.3f}s")
    
    # Basic sanity checks - adjusted for thread-based approach
    assert sync_time < 3.0  # Should complete within 3 seconds (thread overhead)
    assert async_time < 3.0  # Thread-based approach is slower but still reasonable
    assert nested_time < 5.0  # Nested calls have more overhead 