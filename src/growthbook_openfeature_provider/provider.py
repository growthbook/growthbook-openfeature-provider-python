from typing import List, Optional, Union, Dict
from dataclasses import dataclass

# OpenFeature imports - based on openfeature-sdk>=0.7.4
from openfeature.provider.provider import AbstractProvider
from openfeature.flag_evaluation import (
    FlagResolutionDetails,
    EvaluationContext,
    Metadata,
    ResolutionDetails,
    Hook,
    Reason,
)

# GrowthBook imports from the multi-context branch
from growthbook.growthbook_client import GrowthBookClient
from growthbook.common_types import Options, UserContext

@dataclass
class GrowthBookProviderOptions:
    """Configuration options for GrowthBook provider"""
    api_host: str
    client_key: str
    decryption_key: str = ""
    cache_ttl: int = 60

class GrowthBookProvider(AbstractProvider):
    def __init__(self, options: GrowthBookProviderOptions):
        """Initialize GrowthBook provider with configuration options"""
        self.gb_options = Options(
            api_host=options.api_host,
            client_key=options.client_key,
            decryption_key=options.decryption_key,
            cache_ttl=options.cache_ttl
        )
        self.client = None

    async def initialize(self):
        """Initialize the GrowthBook client"""
        self.client = GrowthBookClient(options=self.gb_options)
        await self.client.initialize()

    def get_metadata(self) -> Metadata:
        """Return provider metadata"""
        return Metadata(name="GrowthBook Provider")

    def get_provider_hooks(self) -> List[Hook]:
        """Return provider-specific hooks"""
        return []

    def _create_user_context(self, evaluation_context: Optional[EvaluationContext] = None) -> UserContext:
        """Convert OpenFeature evaluation context to GrowthBook user context"""
        if not evaluation_context:
            return UserContext()

        attributes = {}
        if evaluation_context.attributes:
            attributes = dict(evaluation_context.attributes)
        
        if evaluation_context.targeting_key:
            attributes['id'] = evaluation_context.targeting_key

        return UserContext(
            attributes=attributes
        )

    def _create_resolution_details(self, flag_key: str, value: any, error_code: str = None) -> ResolutionDetails:
        """Create resolution details object"""
        return ResolutionDetails(
            value=value,
            variant=None,  # GrowthBook doesn't provide variant info in this format
            reason="TARGETING_MATCH" if not error_code else error_code,
            error_code=error_code,
            error_message=None,
            flag_metadata=None
        )

    async def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        """Resolve boolean feature flags"""
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code="PROVIDER_NOT_READY"
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = await self.client.is_on(flag_key, user_context)
            return FlagResolutionDetails(
                value=result,
                reason="TARGETING_MATCH"
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code="GENERAL",
                error_message=str(e)
            )

    async def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        """Resolve string feature flags"""
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code="PROVIDER_NOT_READY"
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = await self.client.get_feature_value(flag_key, default_value, user_context)
            return FlagResolutionDetails(
                value=str(result),
                reason="TARGETING_MATCH"
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code="GENERAL",
                error_message=str(e)
            )

    async def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        """Resolve integer feature flags"""
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code="PROVIDER_NOT_READY"
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = await self.client.get_feature_value(flag_key, default_value, user_context)
            return FlagResolutionDetails(
                value=int(result),
                reason="TARGETING_MATCH"
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code="GENERAL",
                error_message=str(e)
            )

    async def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        """Resolve float feature flags"""
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code="PROVIDER_NOT_READY"
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = await self.client.get_feature_value(flag_key, default_value, user_context)
            return FlagResolutionDetails(
                value=float(result),
                reason="TARGETING_MATCH"
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code="GENERAL",
                error_message=str(e)
            )

    async def resolve_object_details(
        self,
        flag_key: str,
        default_value: Union[dict, list],
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[Union[dict, list]]:
        """Resolve object feature flags"""
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code="PROVIDER_NOT_READY"
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = await self.client.get_feature_value(flag_key, default_value, user_context)
            return FlagResolutionDetails(
                value=result,
                reason="TARGETING_MATCH"
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code="GENERAL",
                error_message=str(e)
            ) 