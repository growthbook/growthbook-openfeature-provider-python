# GrowthBook OpenFeature Provider

This package provides a GrowthBook provider implementation for OpenFeature SDK in Python.

## Installation

bash
pip install growthbook-openfeature-provider
python
from openfeature import api
from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
async def main():
options = GrowthBookProviderOptions(
api_host="<https://cdn.growthbook.io>",
client_key="your-client-key"
)
provider = GrowthBookProvider(options)
await provider.initialize()
api.set_provider(provider)
client = api.get_client()

## Use feature flags

value = await client.get_boolean_value("my-feature", False)
print(f"Feature flag value: {value}")
:
bash
git clone <https://github.com/yourusername/growthbook-openfeature-provider.git>
cd growthbook-openfeature-provider
:
bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
:
bash
pip install -e ".[dev]"
:
bash
pytest
:
bash
black .
isort .
