import pytest
from unittest.mock import Mock, patch, AsyncMock
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import Reason, ErrorCode

from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
from growthbook import InMemoryStickyBucketService
from growthbook.common_types import Experiment

# Mock experiment viewed callback
experiment_viewed = Mock()

@pytest.fixture
def provider_options():
    return GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        enabled=True,
        qa_mode=False,
        on_experiment_viewed=experiment_viewed,
        sticky_bucket_service=InMemoryStickyBucketService()
    )

@pytest.fixture
def provider(provider_options):
    return GrowthBookProvider(provider_options)

@pytest.fixture
def evaluation_context():
    return EvaluationContext(
        targeting_key="user-123",
        attributes={
            "country": "US",
            "email": "test@example.com"
        }
    )

@pytest.mark.asyncio
async def test_provider_initialization(provider):
    with patch('growthbook.growthbook_client.GrowthBookClient.initialize') as mock_init:
        await provider.initialize()
        mock_init.assert_called_once()
        assert provider.client is not None

@pytest.mark.asyncio
async def test_provider_disabled():
    disabled_options = GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        enabled=False
    )
    provider = GrowthBookProvider(disabled_options)
    await provider.initialize()
    
    result = await provider.resolve_boolean_details("test-flag", False)
    assert result.value is False
    assert result.reason == Reason.DISABLED

@pytest.mark.asyncio
async def test_qa_mode():
    qa_options = GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        qa_mode=True
    )
    provider = GrowthBookProvider(qa_options)
    await provider.initialize()
    
    # QA mode should still work with feature evaluation
    with patch('growthbook.growthbook_client.GrowthBookClient.is_on', return_value=True):
        result = await provider.resolve_boolean_details("test-flag", False)
        assert result.value is True

@pytest.mark.asyncio
async def test_experiment_viewed_callback(provider, evaluation_context):
    await provider.initialize()
    
    # Mock an experiment evaluation that triggers the callback
    mock_experiment = Experiment(key="test-exp")
    with patch('growthbook.growthbook_client.GrowthBookClient.is_on', 
              side_effect=lambda *args, **kwargs: experiment_viewed(mock_experiment) or True):
        result = await provider.resolve_boolean_details("test-flag", False, evaluation_context)
        assert result.value is True
        experiment_viewed.assert_called_once_with(mock_experiment)

@pytest.mark.asyncio
async def test_sticky_bucketing(provider_options, evaluation_context):
    provider = GrowthBookProvider(provider_options)
    await provider.initialize()
    
    # Test that sticky bucket service is used for consistent assignments
    user_id = evaluation_context.targeting_key
    experiment_id = "test-exp"
    
    # First evaluation
    with patch('growthbook.growthbook_client.GrowthBookClient.is_on', return_value=True):
        result1 = await provider.resolve_boolean_details(experiment_id, False, evaluation_context)
    
    # Second evaluation should use cached value from sticky bucket service
    with patch('growthbook.growthbook_client.GrowthBookClient.is_on', return_value=False):
        result2 = await provider.resolve_boolean_details(experiment_id, False, evaluation_context)
    
    assert result1.value == result2.value

@pytest.mark.asyncio
async def test_resolve_boolean_flag(provider, evaluation_context):
    with patch('growthbook.growthbook_client.GrowthBookClient.is_on') as mock_is_on:
        mock_is_on.return_value = True
        await provider.initialize()
        
        result = await provider.resolve_boolean_details(
            "test-flag",
            False,
            evaluation_context
        )
        
        assert result.value is True
        assert result.reason == Reason.TARGETING_MATCH
        mock_is_on.assert_called_once()

@pytest.mark.asyncio
async def test_provider_not_ready(provider, evaluation_context):
    # Don't initialize the provider
    result = await provider.resolve_boolean_details(
        "test-flag",
        False,
        evaluation_context
    )
    
    assert result.value is False
    assert result.error_code == ErrorCode.PROVIDER_NOT_READY

@pytest.mark.asyncio
async def test_error_handling(provider, evaluation_context):
    with patch('growthbook.growthbook_client.GrowthBookClient.get_feature_value') as mock_get_value:
        mock_get_value.side_effect = Exception("Test error")
        await provider.initialize()
        
        result = await provider.resolve_string_details(
            "test-flag",
            "default",
            evaluation_context
        )
        
        assert result.value == "default"
        assert result.error_code == ErrorCode.GENERAL
        assert "Test error" in result.error_message

def test_evaluation_context_conversion(provider, evaluation_context):
    user_context = provider._create_user_context(evaluation_context)
    
    assert user_context.attributes["id"] == "user-123"
    assert user_context.attributes["country"] == "US"
    assert user_context.attributes["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_resolve_string_details(provider, evaluation_context):
    with patch('growthbook.growthbook_client.GrowthBookClient.get_feature_value') as mock_get_value:
        mock_get_value.return_value = "red"
        await provider.initialize()
        
        result = await provider.resolve_string_details(
            "button-color",
            "blue",
            evaluation_context
        )
        
        assert result.value == "red"
        assert result.reason == Reason.TARGETING_MATCH