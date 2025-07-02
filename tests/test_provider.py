"""
Comprehensive test suite for the GrowthBook OpenFeature Provider.

This test suite covers:
1. Core provider functionality with mocked features
2. Native async methods (OpenFeature SDK 0.8.1+)
3. Integration tests with real GrowthBook API
4. Legacy compatibility (run_async_legacy)
5. Error handling and edge cases
"""
import pytest
import asyncio
import logging
import time
from unittest.mock import patch, AsyncMock, MagicMock
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import Reason, ErrorCode, FlagResolutionDetails
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
from growthbook_openfeature_provider.provider import run_async_legacy
from growthbook.common_types import UserContext
from dataclasses import dataclass
from typing import Any, Optional

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class MockFeatureResult:
    """Mock feature result from GrowthBook"""
    value: Any
    ruleId: Optional[str] = None
    experimentResult: Any = None

@pytest.fixture
async def mock_features():
    """Mock feature data that would come from GrowthBook API"""
    return {
        "features": {
            "test-flag": {
                "defaultValue": True,
                "rules": []
            },
            "targeted-flag": {
                "defaultValue": False,
                "rules": [{
                    "id": "rule-1",
                    "condition": {
                        "country": "US"
                    },
                    "force": True
                }]
            },
            "experiment-flag": {
                "defaultValue": "control",
                "rules": [{
                    "key": "my-experiment",
                    "variations": ["A", "B"],
                    "coverage": 1.0,
                    "weights": [0.5, 0.5]
                }]
            }
        },
        "savedGroups": {}
    }

@pytest.fixture
def mocked_provider():
    """Create provider with mocked features for core functionality testing"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        enabled=True
    ))
    
    # Mock the feature repository loading
    with patch('growthbook.FeatureRepository.load_features_async') as mock_load:
        # Mock comprehensive feature set
        mock_load.return_value = {
            "features": {
                "simple-flag": {
                    "defaultValue": True,
                    "rules": []
                },
                "targeted-flag": {
                    "defaultValue": False,
                    "rules": [{
                        "id": "rule-1",
                        "condition": {"country": "US"},
                        "force": True
                    }]
                },
                "experiment": {
                    "defaultValue": "control",
                    "rules": [{
                        "variations": ["A", "B"],
                        "key": "my-test",
                        "coverage": 1.0,
                        "weights": [0.5, 0.5]
                    }]
                },
                "string-flag": {
                    "defaultValue": "default-string",
                    "rules": []
                },
                "number-flag": {
                    "defaultValue": 42,
                    "rules": []
                },
                "object-flag": {
                    "defaultValue": {"key": "value"},
                    "rules": []
                }
            },
            "savedGroups": {}
        }
        
        # Initialize the provider synchronously for sync tests
        provider.initialize_sync()
        provider.initialized = True
    
    yield provider
    
    # Clean up
    if provider.client:
        run_async_legacy(provider.close())


@pytest.fixture
async def async_mocked_provider():
    """Create provider with mocked features for async testing"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        enabled=True
    ))
    
    # Mock the feature repository loading
    with patch('growthbook.FeatureRepository.load_features_async') as mock_load:
        # Mock comprehensive feature set
        mock_load.return_value = {
            "features": {
                "simple-flag": {
                    "defaultValue": True,
                    "rules": []
                },
                "targeted-flag": {
                    "defaultValue": False,
                    "rules": [{
                        "id": "rule-1",
                        "condition": {"country": "US"},
                        "force": True
                    }]
                },
                "experiment": {
                    "defaultValue": "control",
                    "rules": [{
                        "variations": ["A", "B"],
                        "key": "my-test",
                        "coverage": 1.0,
                        "weights": [0.5, 0.5]
                    }]
                },
                "string-flag": {
                    "defaultValue": "default-string",
                    "rules": []
                },
                "number-flag": {
                    "defaultValue": 42,
                    "rules": []
                },
                "object-flag": {
                    "defaultValue": {"key": "value"},
                    "rules": []
                }
            },
            "savedGroups": {}
        }
        
        # Initialize the provider asynchronously
        await provider.initialize()
        provider.initialized = True
    
    yield provider
    
    # Clean up
    if provider.client:
        await provider.client.close()


@pytest.fixture
def evaluation_context():
    """Standard evaluation context for testing"""
    return EvaluationContext(
        targeting_key="user-123",
        attributes={
            "id": "user-123",
            "country": "US",
            "deviceId": "device-123",
            "premium": True
        }
    )


def test_provider_async_evaluation():
    """Test basic async functionality of the GrowthBook provider"""
    # Create provider with test configuration
    provider = GrowthBookProvider(
        GrowthBookProviderOptions(
            api_host="https://cdn.growthbook.io",
            client_key="test-key",
        )
    )
    
    try:
        # Initialize the provider
        # Note: This will fail to fetch features but should not block
        provider.initialize_sync()
        
        # Register with OpenFeature
        api.set_provider(provider)
        
        # Get a client
        client = api.get_client()
        
        # Create evaluation context
        context = EvaluationContext(
            targeting_key="user-123",
            attributes={
                "country": "US",
                "deviceId": "device-456",
                "premium": True,
            },
        )
        
        # Set the evaluation context
        api.set_evaluation_context(context)
        
        # Test flag evaluation - should return default value
        bool_flag = client.get_boolean_value("test-flag", False)
        logger.info(f"Test flag value-: {bool_flag}")
        
        # Verify we got a result (should be the default value)
        assert bool_flag is False, "Expected default value (False) when features cannot be fetched"
        
    finally:
        # Clean up
        run_async_legacy(provider.close())

def test_provider_with_real_api():
    """Test the provider with a real GrowthBook API connection."""
    logger.info("Starting test_provider_with_real_api")
    
    try:
        # Initialize the provider
        logger.info("Initializing provider")
        provider = GrowthBookProvider(
            GrowthBookProviderOptions(
                api_host="https://cdn.growthbook.io",
                client_key="sdk-IZ02s9Y4Z1LZVO",
                cache_ttl=0  # Disable caching for testing
            )
        )
        
        # Initialize the provider with a timeout
        logger.info("Waiting for provider initialization")
        try:
            provider.initialize_sync()
            logger.info("Provider initialized successfully")
        except Exception as e:
            logger.error(f"Provider initialization failed: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Create test context
        logger.info("Creating test context")
        test_context = EvaluationContext(
            targeting_key="test-user",
            attributes={
                "id": "test-user",
                "country": "US",
                "deviceId": "test-device",
                "superAdmin": True,
                "organizationId": "org_24yyifrkf649iz6",
                "cloud": True,
                "accountPlan": "enterprise"
            }
        )
        
        # Register with OpenFeature
        logger.info("Registering provider with OpenFeature")
        api.set_provider(provider)
        client = api.get_client()
        
        # Test boolean flag (ff1)
        logger.info("Testing boolean flag ff1")
        try:
            result = client.get_boolean_details("ff1", True, test_context)
            logger.info(f"Boolean flag result: {result}")
            assert result.value is False  # Default value from API
            assert isinstance(result.value, bool)
        except Exception as e:
            logger.error(f"Error testing boolean flag: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Test boolean flag with targeting (ff_2)
        logger.info("Testing boolean flag ff_2")
        try:
            result = client.get_boolean_details("ff_2", False, test_context)
            logger.info(f"Boolean flag result: {result}")
            assert result.value is True  # Should be true due to superAdmin and org targeting
            assert isinstance(result.value, bool)
        except Exception as e:
            logger.error(f"Error testing boolean flag: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Test string flag (ff_3_string)
        logger.info("Testing string flag ff_3_string")
        try:
            result = client.get_string_details("ff_3_string", "default", test_context)
            logger.info(f"String flag result: {result}")
            assert result.value == "forced 1"  # Should be forced due to targeting
            assert isinstance(result.value, str)
        except Exception as e:
            logger.error(f"Error testing string flag: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Test number flag (ff_num)
        logger.info("Testing number flag ff_num")
        try:
            result = client.get_integer_details("ff_num", 0, test_context)
            logger.info(f"Number flag result: {result}")
            assert result.value == 1  # Default value from API
            assert isinstance(result.value, int)
        except Exception as e:
            logger.error(f"Error testing number flag: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        # Test JSON flag (ff_4_json)
        logger.info("Testing JSON flag ff_4_json")
        try:
            result = client.get_object_details("ff_4_json", {}, test_context)
            logger.info(f"JSON flag result: {result}")
            assert result.value == {}  # First rule forces empty object
            assert isinstance(result.value, dict)
        except Exception as e:
            logger.error(f"Error testing JSON flag: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            raise
        
        logger.info("All tests completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        raise
    finally:
        logger.info("Test cleanup")
        if 'provider' in locals():
            run_async_legacy(provider.close())
            logger.info("Provider shut down") 

def test_simple_flag_evaluation(mocked_provider, evaluation_context):
    """Test basic flag evaluation with default values"""
    provider = mocked_provider
    
    result = provider.resolve_boolean_details("simple-flag", False, evaluation_context)
    
    assert isinstance(result, FlagResolutionDetails)
    assert result.value is True
    assert result.reason == Reason.DEFAULT

def test_targeting_rules(mocked_provider):
    """Test targeting rules evaluation"""
    provider = mocked_provider
    
    # User in US should match targeting rule
    us_context = EvaluationContext(
        targeting_key="us-user",
        attributes={"country": "US"}
    )
    
    result = provider.resolve_boolean_details("targeted-flag", False, us_context)
    assert result.value is True
    assert result.reason == Reason.TARGETING_MATCH
    
    # User not in US should get default
    uk_context = EvaluationContext(
        targeting_key="uk-user", 
        attributes={"country": "UK"}
    )
    
    result = provider.resolve_boolean_details("targeted-flag", False, uk_context)
    assert result.value is False
    assert result.reason == Reason.DEFAULT

def test_experiment_consistency(mocked_provider, evaluation_context):
    """Test that experiment variations are consistent for same user"""
    provider = mocked_provider
    
    # Same user should get same variation
    first_result = provider.resolve_string_details("experiment", "control", evaluation_context)
    second_result = provider.resolve_string_details("experiment", "control", evaluation_context)
    
    assert first_result.value == second_result.value
    assert first_result.reason == Reason.SPLIT
    assert first_result.variant is not None
    assert second_result.variant == first_result.variant

def test_unknown_flag(mocked_provider, evaluation_context):
    """Test behavior with unknown flags returns default value"""
    provider = mocked_provider
    
    result = provider.resolve_boolean_details("unknown-flag", False, evaluation_context)
    
    assert result.value is False
    assert result.reason == Reason.DEFAULT

def test_provider_not_ready():
    """Test behavior when provider is not initialized"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io", 
        client_key="invalid-key"
    ))
    # Don't initialize
    
    context = EvaluationContext(targeting_key="test-user")
    result = provider.resolve_boolean_details("any-flag", False, context)
    
    assert result.value is False
    assert result.error_code == ErrorCode.PROVIDER_NOT_READY

def test_context_mapping():
    """Test OpenFeature context to GrowthBook context mapping"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    ))
    
    # Create OpenFeature context
    of_context = EvaluationContext(
        targeting_key="user-123",
        attributes={"country": "US", "premium": True, "age": 25}
    )
    
    # Convert to GrowthBook context
    gb_context = provider._create_user_context(of_context)
    
    # Verify mapping
    assert gb_context.attributes.get("id") == "user-123"
    assert gb_context.attributes.get("country") == "US"
    assert gb_context.attributes.get("premium") is True
    assert gb_context.attributes.get("age") == 25

def test_all_flag_types(mocked_provider, evaluation_context):
    """Test all supported flag types work correctly"""
    provider = mocked_provider
    
    # Boolean
    bool_result = provider.resolve_boolean_details("simple-flag", False, evaluation_context)
    assert isinstance(bool_result.value, bool)
    assert bool_result.value is True
    
    # String
    str_result = provider.resolve_string_details("string-flag", "fallback", evaluation_context)
    assert isinstance(str_result.value, str)
    assert str_result.value == "default-string"
    
    # Integer
    int_result = provider.resolve_integer_details("number-flag", 0, evaluation_context)
    assert isinstance(int_result.value, int)
    assert int_result.value == 42
    
    # Float
    float_result = provider.resolve_float_details("number-flag", 0.0, evaluation_context)
    assert isinstance(float_result.value, float)
    assert float_result.value == 42.0
    
    # Object
    obj_result = provider.resolve_object_details("object-flag", {}, evaluation_context)
    assert isinstance(obj_result.value, dict)
    assert obj_result.value == {"key": "value"}

@pytest.mark.asyncio
async def test_native_async_boolean_details(async_mocked_provider, evaluation_context):
    """Test native async boolean flag evaluation"""
    provider = async_mocked_provider
    
    result = await provider.resolve_boolean_details_async("simple-flag", False, evaluation_context)
    
    assert isinstance(result, FlagResolutionDetails)
    assert not isinstance(result, asyncio.Task)
    assert result.value is True
    assert result.reason == Reason.DEFAULT

@pytest.mark.asyncio
async def test_native_async_all_types(async_mocked_provider, evaluation_context):
    """Test all native async methods work correctly"""
    provider = async_mocked_provider
    
    # Test all async methods
    bool_result = await provider.resolve_boolean_details_async("simple-flag", False, evaluation_context)
    str_result = await provider.resolve_string_details_async("string-flag", "fallback", evaluation_context)
    int_result = await provider.resolve_integer_details_async("number-flag", 0, evaluation_context)
    float_result = await provider.resolve_float_details_async("number-flag", 0.0, evaluation_context)
    obj_result = await provider.resolve_object_details_async("object-flag", {}, evaluation_context)
    
    # Verify all return proper types
    assert isinstance(bool_result, FlagResolutionDetails)
    assert isinstance(str_result, FlagResolutionDetails)
    assert isinstance(int_result, FlagResolutionDetails)
    assert isinstance(float_result, FlagResolutionDetails)
    assert isinstance(obj_result, FlagResolutionDetails)
    
    # Verify values
    assert bool_result.value is True
    assert str_result.value == "default-string"
    assert int_result.value == 42
    assert float_result.value == 42.0
    assert obj_result.value == {"key": "value"}

@pytest.mark.asyncio
async def test_concurrent_async_calls(async_mocked_provider):
    """Test concurrent async flag evaluations work correctly"""
    provider = async_mocked_provider
    
    async def evaluate_flag(flag_name: str, user_id: str):
        context = EvaluationContext(
            targeting_key=user_id,
            attributes={"id": user_id}
        )
        return await provider.resolve_boolean_details_async(flag_name, False, context)
    
    # Make 10 concurrent calls
    tasks = [evaluate_flag("simple-flag", f"user-{i}") for i in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Verify all results
    assert len(results) == 10
    for result in results:
        assert isinstance(result, FlagResolutionDetails)
        assert not isinstance(result, asyncio.Task)
        assert result.value is True  # simple-flag default

@pytest.mark.asyncio
async def test_fastapi_style_usage(async_mocked_provider):
    """Test usage pattern similar to FastAPI applications"""
    provider = async_mocked_provider
    
    async def simulate_fastapi_endpoint(user_id: str):
        """Simulate a FastAPI endpoint using the provider"""
        context = EvaluationContext(
            targeting_key=user_id,
            attributes={
                "id": user_id,
                "source": "api",
                "environment": "test"
            }
        )
        
        # Multiple concurrent flag evaluations
        feature_enabled = await provider.resolve_boolean_details_async("simple-flag", False, context)
        experiment_variant = await provider.resolve_string_details_async("experiment", "control", context)
        config_value = await provider.resolve_integer_details_async("number-flag", 100, context)
        
        return {
            "feature_enabled": feature_enabled.value,
            "experiment_variant": experiment_variant.value,
            "config_value": config_value.value
        }
    
    # Call the simulated endpoint
    result = await simulate_fastapi_endpoint("fastapi-user")
    
    # Verify the result
    assert isinstance(result, dict)
    assert result["feature_enabled"] is True  # simple-flag default
    assert result["experiment_variant"] in ["A", "B"]  # experiment variation
    assert result["config_value"] == 42  # number-flag default

@pytest.mark.asyncio
async def test_async_performance_no_blocking():
    """Test that async methods don't block the event loop"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    ))
    
    with patch.object(provider, 'client') as mock_client:
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.eval_feature = AsyncMock(return_value=None)
        
        await provider.initialize()
        provider.initialized = True
        
        context = EvaluationContext(targeting_key="test-user")
        
        # This should complete quickly without blocking
        start_time = time.time()
        result = await provider.resolve_boolean_details_async("test-flag", False, context)
        elapsed = time.time() - start_time
        
        # Should complete very quickly (< 100ms) since we're mocking
        assert elapsed < 0.1
        assert isinstance(result, FlagResolutionDetails)

def test_run_async_legacy_in_sync_context():
    """Test run_async_legacy works correctly in sync contexts"""
    async def test_coro():
        return "test_result"
    
    # Should work in sync context
    result = run_async_legacy(test_coro())
    assert result == "test_result"

@pytest.mark.asyncio
async def test_run_async_legacy_works_in_async_context():
    """Test that run_async_legacy works correctly when called from async context using ThreadPoolExecutor"""
    async def test_coro():
        return "test_result"
    
    # Should work correctly in async context using ThreadPoolExecutor
    result = run_async_legacy(test_coro())
    assert result == "test_result"

def test_run_async_legacy_error_propagation():
    """Test run_async_legacy properly propagates errors"""
    async def test_coro():
        raise ValueError("test error message")
    
    # Should propagate the error
    with pytest.raises(ValueError, match="test error message"):
        run_async_legacy(test_coro())


def test_run_async_legacy_performance():
    """Test performance of run_async_legacy in sync contexts"""
    import time
    
    async def dummy_coro():
        await asyncio.sleep(0.001)  # Small delay to simulate work
        return "result"
    
    # Test sync context performance
    start = time.time()
    for _ in range(10):  # Reduced iterations for faster testing
        result = run_async_legacy(dummy_coro())
        assert result == "result"
    sync_time = time.time() - start
    
    # Should complete in reasonable time (allow generous margin)
    assert sync_time < 5

def test_legacy_sync_usage_still_works():
    """Test that legacy sync usage patterns still work"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    ))
    
    with patch.object(provider, 'client') as mock_client:
        mock_client.initialize = AsyncMock(return_value=True)
        mock_client.eval_feature = AsyncMock(return_value=None)
        
        # Sync initialization should still work
        provider.initialize_sync()
        provider.initialized = True
        
        # Sync flag evaluation should still work
        context = EvaluationContext(targeting_key="sync-user")
        result = provider.resolve_boolean_details("sync-flag", False, context)
        
        assert isinstance(result, FlagResolutionDetails)
        assert result.value is False

def test_provider_basic_functionality_without_api():
    """Test basic provider functionality when API is unavailable"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
    ))
    
    try:
        # Initialize - will fail to fetch features but should not crash
        provider.initialize_sync()
        
        # Register with OpenFeature
        api.set_provider(provider)
        client = api.get_client()
        
        # Create evaluation context
        context = EvaluationContext(
            targeting_key="user-123",
            attributes={"country": "US", "premium": True}
        )
        
        # Test flag evaluation - should return default values
        bool_flag = client.get_boolean_value("test-flag", False)
        str_flag = client.get_string_value("string-flag", "default")
        int_flag = client.get_integer_value("int-flag", 42)
        
        # Should get default values when features cannot be fetched
        assert bool_flag is False
        assert str_flag == "default"
        assert int_flag == 42
        
    finally:
        run_async_legacy(provider.close())

@pytest.mark.asyncio
async def test_provider_close_async():
    """Test that provider close works properly in async context"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    ))
    
    # Mock the client
    mock_client = AsyncMock()
    mock_client.initialize = AsyncMock(return_value=True)
    mock_client.eval_feature = AsyncMock(return_value=None)
    mock_client.close = AsyncMock()
    
    provider.client = mock_client
    await provider.initialize()
    provider.initialized = True
    
    # Close should work without issues
    await provider.close()
    
    # Provider should be properly cleaned up
    assert provider.client is None
    assert provider.initialized is False

def test_sync_and_async_coexistence(mocked_provider, evaluation_context):
    """Test that sync and async methods can coexist and work correctly"""
    provider = mocked_provider
    
    # Sync method should work
    sync_result = provider.resolve_boolean_details("simple-flag", False, evaluation_context)
    assert isinstance(sync_result, FlagResolutionDetails)
    assert sync_result.value is True
    
    # Provider should be ready for async methods too
    assert provider.initialized is True
    assert provider.client is not None 