import pytest
from unittest.mock import Mock, patch
from openfeature.evaluation_context import EvaluationContext
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions

@pytest.fixture
def provider():
    options = GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    )
    return GrowthBookProvider(options)

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
    with patch('growthbook.GrowthBookClient.initialize') as mock_init:
        await provider.initialize()
        mock_init.assert_called_once()
        assert provider.client is not None

@pytest.mark.asyncio
async def test_resolve_boolean_flag(provider, evaluation_context):
    with patch('growthbook.GrowthBookClient.is_on') as mock_is_on:
        mock_is_on.return_value = True
        await provider.initialize()
        
        result = await provider.resolve_boolean_details(
            "test-flag",
            False,
            evaluation_context
        )
        
        assert result.value is True
        assert result.reason == "TARGETING_MATCH"
        mock_is_on.assert_called_once()

@pytest.mark.asyncio
async def test_resolve_string_flag(provider, evaluation_context):
    with patch('growthbook.GrowthBookClient.get_feature_value') as mock_get_value:
        mock_get_value.return_value = "red"
        await provider.initialize()
        
        result = await provider.resolve_string_details(
            "button-color",
            "blue",
            evaluation_context
        )
        
        assert result.value == "red"
        assert result.reason == "TARGETING_MATCH"
        mock_get_value.assert_called_once()

@pytest.mark.asyncio
async def test_provider_not_ready(provider, evaluation_context):
    # Don't initialize the provider
    result = await provider.resolve_boolean_details(
        "test-flag",
        False,
        evaluation_context
    )
    
    assert result.value is False
    assert result.error_code == "PROVIDER_NOT_READY"

@pytest.mark.asyncio
async def test_error_handling(provider, evaluation_context):
    with patch('growthbook.GrowthBookClient.get_feature_value') as mock_get_value:
        mock_get_value.side_effect = Exception("Test error")
        await provider.initialize()
        
        result = await provider.resolve_string_details(
            "test-flag",
            "default",
            evaluation_context
        )
        
        assert result.value == "default"
        assert result.error_code == "GENERAL"
        assert "Test error" in result.error_message

def test_evaluation_context_conversion(provider, evaluation_context):
    user_context = provider._create_user_context(evaluation_context)
    
    assert user_context.attributes["id"] == "user-123"
    assert user_context.attributes["country"] == "US"
    assert user_context.attributes["email"] == "test@example.com"