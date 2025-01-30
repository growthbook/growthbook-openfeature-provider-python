from typing import List, Optional, Union, Dict, Any, Callable
from dataclasses import dataclass, field

# OpenFeature imports - based on openfeature-sdk>=0.7.4
from openfeature.provider.provider import AbstractProvider
from openfeature.provider import Metadata
from openfeature.evaluation_context import EvaluationContext
from openfeature.flag_evaluation import (
    FlagResolutionDetails,
    Hook,
    Reason,
    ErrorCode,
)

# GrowthBook imports from the multi-context branch
from growthbook.growthbook_client import GrowthBookClient
from growthbook.common_types import Options, UserContext, Experiment
from growthbook import AbstractStickyBucketService

@dataclass
class GrowthBookProviderOptions:
    """Configuration options for GrowthBook provider.
    
    Args:
        api_host: URL of the GrowthBook API
        client_key: API key for authentication
        decryption_key: Optional key for encrypted features
        cache_ttl: Cache duration in seconds (default: 60)
        enabled: Whether GrowthBook is enabled (default: True)
        qa_mode: Enable QA mode for testing (default: False)
        on_experiment_viewed: Optional callback when experiments are viewed
        sticky_bucket_service: Optional service for consistent experiment assignments
    """
    api_host: str
    client_key: str
    decryption_key: str = ""
    cache_ttl: int = 60
    enabled: bool = True
    qa_mode: bool = False
    on_experiment_viewed: Optional[Callable[[Experiment], None]] = None
    sticky_bucket_service: Optional[AbstractStickyBucketService] = None

class GrowthBookProvider(AbstractProvider):
    """GrowthBook provider implementation for OpenFeature.
    
    Note: While OpenFeature supports optional evaluation context,
    GrowthBook requires user context for proper targeting. It's recommended
    to always provide evaluation context with targeting information.
    """
    
    def __init__(self, options: GrowthBookProviderOptions):
        """Initialize GrowthBook provider with configuration options"""
        self.gb_options = Options(
            api_host=options.api_host,
            client_key=options.client_key,
            decryption_key=options.decryption_key,
            cache_ttl=options.cache_ttl,
            enabled=options.enabled,
            qa_mode=options.qa_mode,
            on_experiment_viewed=options.on_experiment_viewed,
            sticky_bucket_service=options.sticky_bucket_service
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
        """Convert OpenFeature evaluation context to GrowthBook user context.
        
        Args:
            evaluation_context: OpenFeature evaluation context containing targeting information
            
        Returns:
            GrowthBook user context
        """
        if not evaluation_context:
            return UserContext()

        attributes = {}
        if evaluation_context.attributes:
            attributes = dict(evaluation_context.attributes)
        
        if evaluation_context.targeting_key:
            attributes['id'] = evaluation_context.targeting_key

        return UserContext(attributes=attributes)

    def _create_flag_resolution(
        self,
        value: Any,
        default_value: Any,
        error: Optional[Exception] = None,
        variant: Optional[str] = None,
    ) -> FlagResolutionDetails:
        """Create flag resolution details with proper error handling.
        
        Args:
            value: The resolved value
            default_value: Default value if resolution fails
            error: Optional exception that occurred during resolution
            variant: Optional variant name from evaluation
            
        Returns:
            Flag resolution details with appropriate error codes and messages
        """
        if not self.client:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        if error:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(error),
                reason=Reason.ERROR
            )

        return FlagResolutionDetails(
            value=value,
            variant=variant,
            reason=Reason.TARGETING_MATCH
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
            return self._create_flag_resolution(result, default_value)
        except Exception as e:
            return self._create_flag_resolution(default_value, default_value, error=e)

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