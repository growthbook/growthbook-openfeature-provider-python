# GrowthBook OpenFeature Provider for Python

[![PyPI version](https://badge.fury.io/py/growthbook-openfeature-provider.svg)](https://badge.fury.io/py/growthbook-openfeature-provider)
[![Build and Test](https://github.com/growthbook/growthbook-openfeature-provider-python/actions/workflows/ci.yml/badge.svg)](https://github.com/growthbook/growthbook-openfeature-provider-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python implementation of an [OpenFeature](https://openfeature.dev/) provider for [GrowthBook](https://www.growthbook.io/), enabling standardized feature flag evaluation in Python applications.

## Requirements

- Python 3.9 or higher
- OpenFeature SDK 0.8.1+

## Features

- Full implementation of the OpenFeature provider interface
- Support for all flag types (boolean, string, integer, float, object)
- Proper context mapping between OpenFeature and GrowthBook
- Asynchronous and synchronous initialization options
- Comprehensive error handling
- Resource cleanup utilities

## Installation

```bash
pip install growthbook-openfeature-provider
```

## Quick Start

### Async Usage (Recommended)

```python
import asyncio
from openfeature.api import OpenFeatureAPI
from openfeature.evaluation_context import EvaluationContext
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions

async def main():
    # Create and initialize the provider
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123"  # Replace with your actual SDK key
    ))

    # Initialize the provider
    await provider.initialize()
    
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
            "premium": True
        }
    )
    

    details = await provider.resolve_boolean_details_async("my-flag", False, context)
    print(f"Flag value: {details.value}, reason: {details.reason}")
    
    # Clean up resources when done
    await provider.close()

# Run the async function
asyncio.run(main())
```

### Synchronous Usage

```python
from openfeature.api import OpenFeatureAPI
from openfeature.evaluation_context import EvaluationContext
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions

# Create provider
provider = GrowthBookProvider(GrowthBookProviderOptions(
    api_host="https://cdn.growthbook.io",
    client_key="sdk-abc123"
))

# Initialize synchronously
provider.initialize_sync()

# Register with OpenFeature
OpenFeatureAPI.set_provider(provider)

# Get a client and evaluate flags
client = OpenFeatureAPI.get_client("my-app")
context = EvaluationContext(
    targeting_key="user-123",
    attributes={"country": "US", "premium": True}
)

value = client.get_boolean_value("my-flag", False, context)
print(f"Flag value: {value}")

# Clean up (can be called from sync context)
import asyncio
asyncio.run(provider.close())
```

## Configuration Options

The `GrowthBookProviderOptions` class accepts the following parameters:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `api_host` | `str` | URL of the GrowthBook API | Required |
| `client_key` | `str` | API key for authentication | Required |
| `decryption_key` | `str` | Key for encrypted features | `""` |
| `cache_ttl` | `int` | Cache duration in seconds | `60` |
| `enabled` | `bool` | Whether GrowthBook is enabled | `True` |
| `qa_mode` | `bool` | Enable QA mode for testing | `False` |
| `on_experiment_viewed` | `Callable` | Callback when experiments are viewed | `None` |
| `sticky_bucket_service` | `AbstractStickyBucketService` | Service for consistent experiment assignments | `None` |

## Evaluation Context

The provider maps OpenFeature evaluation context to GrowthBook user context:

- The `targeting_key` is mapped to the `id` attribute
- All other attributes are passed through directly

Example:

```python
context = EvaluationContext(
    targeting_key="user-123",
    attributes={
        "country": "US",
        "deviceId": "device-456",
        "premium": True
    }
)
```

This creates a GrowthBook context with:

```json
{
  "id": "user-123",
  "country": "US",
  "deviceId": "device-456",
  "premium": true
}
```

## Flag Evaluation

The provider supports all OpenFeature flag types with both synchronous and asynchronous methods:

### Synchronous Methods (for sync contexts)

```python
# Boolean flags
boolean_value = client.get_boolean_value("my-boolean-flag", False, context)

# String flags
string_value = client.get_string_value("my-string-flag", "default", context)

# Integer flags
int_value = client.get_integer_value("my-number-flag", 0, context)

# Float flags
float_value = client.get_float_value("my-float-flag", 0.0, context)

# Object flags
object_value = client.get_object_value("my-object-flag", {"default": True}, context)
```

### Asynchronous Methods (recommended for async contexts)

```python
# Boolean flags
boolean_details = await provider.resolve_boolean_details_async("my-boolean-flag", False, context)
boolean_value = boolean_details.value

# String flags
string_details = await provider.resolve_string_details_async("my-string-flag", "default", context)
string_value = string_details.value

# Integer flags
int_details = await provider.resolve_integer_details_async("my-number-flag", 0, context)
int_value = int_details.value

# Float flags
float_details = await provider.resolve_float_details_async("my-float-flag", 0.0, context)
float_value = float_details.value

# Object flags
object_details = await provider.resolve_object_details_async("my-object-flag", {"default": True}, context)
object_value = object_details.value
```

### Evaluation Results

Evaluation results include `value`, `reason` and `variant`:

```python
# Asynchronous evaluation
details = await provider.resolve_boolean_details_async("my-flag", False, context)
print(f"Value: {details.value}")
print(f"Reason: {details.reason}")
print(f"Variant: {details.variant}")
```

## Error Handling

The provider handles various error conditions gracefully:

- **Uninitialized provider**: Returns `PROVIDER_NOT_READY` error
- **Missing targeting key**: Returns `TARGETING_KEY_MISSING` error
- **Type conversion errors**: Returns `TYPE_MISMATCH` error
- **Network failures**: Returns default values with `ERROR` reason
- **General exceptions**: Returns `GENERAL` error with message

## Resource Cleanup

Always clean up resources when done:

```python
# Async cleanup (recommended)
await provider.close()

# Sync cleanup
import asyncio
asyncio.run(provider.close())
```

## Examples

See the [examples](./examples) directory for more usage examples, including:

- Basic usage patterns
- FastAPI integration
- Error handling
- Performance optimization

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [OpenFeature](https://openfeature.dev/) - For the feature flag standard
- [GrowthBook](https://www.growthbook.io/) - For the feature flagging and experimentation platform
