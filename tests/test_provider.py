import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from openfeature import api
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import Reason
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
from growthbook_openfeature_provider.provider import run_async
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
        run_async(provider.close())

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
            run_async(provider.close())
            logger.info("Provider shut down") 