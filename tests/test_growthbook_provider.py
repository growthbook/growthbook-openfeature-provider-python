import pytest
from unittest.mock import patch, AsyncMock
from openfeature.provider import AbstractProvider
from openfeature.flag_evaluation import Reason, ErrorCode
from openfeature.evaluation_context import EvaluationContext

from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions

@pytest.fixture
async def provider():
    """Create provider with mocked initialization"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key",
        enabled=True
    ))
    
    # Only mock the feature repository loading
    with patch('growthbook.FeatureRepository.load_features_async') as mock_load:
        # Mock the feature repository response (API format)
        mock_load.return_value = {
            "features": {
                "simple-flag": {
                    "defaultValue": True,
                    "rules": []
                },
                "targeted-flag": {
                    "defaultValue": False,
                    "rules": [{
                        "id": "id",
                        "variations": ["a", "b", "c"]
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
                }
            },
            "savedGroups": {}
        }
        
        # Initialize the provider
        await provider.initialize()
        provider.initialized = True
    
    # Return the provider for testing
    yield provider
    
    # Clean up resources
    if provider.client:
        await provider.client.close()

@pytest.fixture
def evaluation_context():
    return EvaluationContext(
        targeting_key="user-123",
        attributes={
            "id": "user-123",
            "country": "US",
            "deviceId": "device-123"
        }
    )

def test_simple_flag_evaluation(provider, evaluation_context):
    """Test basic flag evaluation"""
    result = provider.resolve_boolean_details(
        "simple-flag",
        False,
        evaluation_context
    )
    assert result.value is True
    assert result.reason == Reason.DEFAULT

def test_targeting_rules(provider, evaluation_context):
    """Test targeting rules evaluation"""

    other_context = EvaluationContext(
        targeting_key="456",
        attributes={"country": "UK"}
    )

    result = provider.resolve_boolean_details(
        "targeted-flag",
        False,
        other_context
    )
    assert result.value is True
    assert result.reason == Reason.TARGETING_MATCH

def test_experiment_consistency(provider, evaluation_context):
    """Test experiment variation assignment"""
    # Same user should get same variation
    first_result = provider.resolve_string_details(
        "experiment",
        "control",
        evaluation_context
    )
    second_result = provider.resolve_string_details(
        "experiment",
        "control",
        evaluation_context
    )
    assert first_result.value == second_result.value
    assert first_result.reason == Reason.SPLIT
    assert first_result.variant is not None

def test_unknown_flag(provider, evaluation_context):
    """Test behavior with unknown flags"""
    result = provider.resolve_boolean_details(
        "unknown-flag",
        False,
        evaluation_context
    )
    assert result.value is False
    assert result.reason == Reason.DEFAULT

def test_provider_not_ready():
    """Test behavior when provider is not initialized"""
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io", 
        client_key="invalid-key"
    ))
    # Don't initialize
    result = provider.resolve_boolean_details(
        "any-flag",
        False,
        evaluation_context
    )
    assert result.value is False
    assert result.error_code == ErrorCode.PROVIDER_NOT_READY

def test_context_mapping():
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="test-key"
    ))
    
    # Create an OpenFeature context
    of_context = EvaluationContext(
        targeting_key="user-123",
        attributes={"country": "US", "premium": True}
    )
    
    # Convert to GrowthBook context
    gb_context = provider._create_user_context(of_context)
    
    # Verify mapping
    assert gb_context.attributes.get("id") == "user-123"
    assert gb_context.attributes.get("country") == "US"
    assert gb_context.attributes.get("premium") is True