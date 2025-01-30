import asyncio
from openfeature import api
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
from openfeature.evaluation_context import EvaluationContext

async def main():
    # Configure the provider
    options = GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123"  # Replace with your client key
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
    
    # Example usage of different flag types
    boolean_flag = await client.get_boolean_value("show-feature", False, context)
    string_flag = await client.get_string_value("button-color", "blue", context)
    number_flag = await client.get_number_value("price", 100, context)
    object_flag = await client.get_object_value("config", {"default": True}, context)
    
    print(f"Boolean flag value: {boolean_flag}")
    print(f"String flag value: {string_flag}")
    print(f"Number flag value: {number_flag}")
    print(f"Object flag value: {object_flag}")

if __name__ == "__main__":
    asyncio.run(main())