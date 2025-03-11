#!/usr/bin/env python3
"""
Basic usage example for GrowthBook OpenFeature Provider.

This example demonstrates how to:
1. Initialize the provider (both async and sync methods)
2. Configure the provider with options
3. Register it with OpenFeature
4. Create evaluation contexts
5. Evaluate different types of feature flags
6. Clean up resources properly
"""

import asyncio
from openfeature.api import OpenFeatureAPI
from openfeature.evaluation_context import EvaluationContext
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions


# Example of synchronous usage
def sync_example():
    print("\n=== Synchronous Usage Example ===")
    
    # Create provider with options
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123",  # Replace with your actual SDK key
        cache_ttl=60,
        enabled=True
    ))
    
    # Initialize synchronously
    provider.initialize_sync()
    
    # Register with OpenFeature
    OpenFeatureAPI.set_provider(provider)
    
    # Get a client
    client = OpenFeatureAPI.get_client("my-app")
    
    # Create an evaluation context with targeting information
    context = EvaluationContext(
        targeting_key="user-123",
        attributes={
            "country": "US",
            "email": "user@example.com",
            "deviceId": "device-456",
            "premium": True
        }
    )
    
    try:
        # Evaluate different types of flags
        print("Boolean flag:", client.get_boolean_value("my-boolean-flag", False, context))
        print("String flag:", client.get_string_value("my-string-flag", "default", context))
        print("Integer flag:", client.get_integer_value("my-number-flag", 0, context))
        print("Float flag:", client.get_float_value("my-float-flag", 0.0, context))
        print("Object flag:", client.get_object_value("my-object-flag", {"default": True}, context))
        
        # Evaluate with details to get more information
        details = client.get_boolean_details("my-boolean-flag", False, context)
        print(f"Flag details: value={details.value}, reason={details.reason}, variant={details.variant}")
        
    finally:
        # Clean up resources
        asyncio.run(provider.close())


# Example of asynchronous usage
async def async_example():
    print("\n=== Asynchronous Usage Example ===")
    
    # Create provider with options
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123",  # Replace with your actual SDK key
        decryption_key="",  # Optional, for encrypted features
        qa_mode=False,
        # Optional callback when experiments are viewed
        on_experiment_viewed=lambda exp: print(f"Experiment viewed: {exp.key}")
    ))
    
    # Initialize asynchronously
    await provider.initialize()
    
    # Register with OpenFeature
    OpenFeatureAPI.set_provider(provider)
    
    # Get a client
    client = OpenFeatureAPI.get_client("my-async-app")
    
    # Create an evaluation context with targeting information
    context = EvaluationContext(
        targeting_key="user-456",
        attributes={
            "country": "CA",
            "email": "user2@example.com",
            "deviceId": "device-789",
            "premium": False
        }
    )
    
    try:
        # Evaluate different types of flags
        print("Boolean flag:", client.get_boolean_value("my-boolean-flag", False, context))
        print("String flag:", client.get_string_value("my-string-flag", "default", context))
        print("Integer flag:", client.get_integer_value("my-number-flag", 0, context))
        print("Float flag:", client.get_float_value("my-float-flag", 0.0, context))
        print("Object flag:", client.get_object_value("my-object-flag", {"default": True}, context))
        
        # Evaluate with details to get more information
        details = client.get_boolean_details("my-boolean-flag", False, context)
        print(f"Flag details: value={details.value}, reason={details.reason}, variant={details.variant}")
        
    finally:
        # Clean up resources
        await provider.close()


# Example of handling errors
def error_handling_example():
    print("\n=== Error Handling Example ===")
    
    # Create provider with invalid options to demonstrate error handling
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://invalid-host.example.com",
        client_key="invalid-key"
    ))
    
    # Initialize (this will likely fail but we'll handle it)
    try:
        provider.initialize_sync()
        print("Provider initialized successfully (unexpected)")
    except Exception as e:
        print(f"Provider initialization failed (expected): {e}")
    
    # Register with OpenFeature anyway to demonstrate error handling in flag evaluation
    OpenFeatureAPI.set_provider(provider)
    client = OpenFeatureAPI.get_client("error-app")
    
    # Create a context
    context = EvaluationContext(targeting_key="user-789")
    
    # Evaluate a flag - should return the default value with an error
    details = client.get_boolean_details("any-flag", True, context)
    print(f"Flag evaluation with uninitialized provider: value={details.value}, reason={details.reason}")
    print(f"Error code: {details.error_code}, Error message: {details.error_message}")
    
    # Always clean up
    asyncio.run(provider.close())


if __name__ == "__main__":
    # Run the synchronous example
    sync_example()
    
    # Run the asynchronous example
    asyncio.run(async_example())
    
    # Run the error handling example
    error_handling_example()