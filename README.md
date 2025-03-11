# GrowthBook OpenFeature Provider for Python

[![PyPI version](https://badge.fury.io/py/growthbook-openfeature-provider.svg)](https://badge.fury.io/py/growthbook-openfeature-provider)
[![Build and Test](https://github.com/growthbook/growthbook-openfeature-provider-python/actions/workflows/ci.yml/badge.svg)](https://github.com/growthbook/growthbook-openfeature-provider-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python implementation of an [OpenFeature](https://openfeature.dev/) provider for [GrowthBook](https://www.growthbook.io/), enabling standardized feature flag evaluation in Python applications.

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

```python
import asyncio
from openfeature.api import OpenFeatureAPI
from openfeature.evaluation_context import EvaluationContext
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions

# Create and initialize the provider
provider = GrowthBookProvider(GrowthBookProviderOptions(
    api_host="https://cdn.growthbook.io",
    client_key="sdk-abc123"  # Replace with your actual SDK key
))

# Initialize the provider
async def setup():
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
    
    # Evaluate a flag
    value = client.get_boolean_value("my-flag", False, context)
    print(f"Flag value: {value}")
    
    # Clean up resources when done
    await provider.close()

# Run the async function
asyncio.run(setup())
```

## Synchronous Usage

If you prefer synchronous initialization:

```python
from openfeature.api import OpenFeatureAPI
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

The provider supports all OpenFeature flag types:

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

For detailed evaluation results:

```python
details = client.get_boolean_details("my-flag", False, context)
print(f"Value: {details.value}")
print(f"Reason: {details.reason}")
print(f"Variant: {details.variant}")
```

## Error Handling

The provider handles various error conditions:

- Uninitialized provider: Returns `PROVIDER_NOT_READY` error
- Missing targeting key: Returns `TARGETING_KEY_MISSING` error
- Type conversion errors: Returns `TYPE_MISMATCH` error
- General exceptions: Returns `GENERAL` error with message

## Resource Cleanup

Always clean up resources when done:

```python
# Async cleanup
await provider.close()

# Sync cleanup
import asyncio
asyncio.run(provider.close())
```

## Examples

See the [examples](./examples) directory for more usage examples.

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
