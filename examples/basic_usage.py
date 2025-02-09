import asyncio
from openfeature import api
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
from openfeature.evaluation_context import EvaluationContext
from growthbook import InMemoryStickyBucketService

async def on_experiment_viewed(experiment):
    print(f"Experiment viewed: {experiment.key}")

async def main():
    # Configure the provider with advanced options
    options = GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123",  # Replace with a valid client key
        enabled=True,
        qa_mode=False,
        on_experiment_viewed=on_experiment_viewed,
        sticky_bucket_service=InMemoryStickyBucketService()
    )
    
    # Create and initialize provider
    provider = GrowthBookProvider(options)
    await provider.initialize()
    
    # Set as OpenFeature provider
    api.set_provider(provider)
    
    # Get OpenFeature client
    client = api.get_client()
    
    # Create evaluation context
    context = EvaluationContext(
        targeting_key="user-123",
        attributes={
            "country": "US",
            "email": "test@example.com"
        }
    )
    
    try:
        # Example usage of different flag types
        boolean_result = client.get_boolean_details("show-feature", False, context)
        string_result = client.get_string_details("button-color", "blue", context)
        number_result = client.get_integer_details("price", 100, context)
        object_result = client.get_object_details("config", {"default": True}, context)
        
        print(f"Boolean flag value: {boolean_result.value}")
        print(f"String flag value: {string_result.value}")
        print(f"Number flag value: {number_result.value}")
        print(f"Object flag value: {object_result.value}")
    except Exception as e:
        print(f"Error evaluating flags: {e}")

if __name__ == "__main__":
    asyncio.run(main())