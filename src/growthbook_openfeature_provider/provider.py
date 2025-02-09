from typing import List, Optional, Union, Dict, Any, Callable
from dataclasses import dataclass, field
import asyncio

# OpenFeature imports - based on openfeature-sdk>=0.7.4
from openfeature.provider import AbstractProvider, Metadata
from openfeature.evaluation_context import EvaluationContext
from openfeature.hook import Hook
from openfeature.flag_evaluation import (
    FlagResolutionDetails,
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

def run_async(coro):
    """Helper function to run async code in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

class GrowthBookProvider(AbstractProvider):
    """GrowthBook provider implementation for OpenFeature.
    
    Note: While OpenFeature supports optional evaluation context,
    GrowthBook requires user context for proper targeting. It's recommended
    to always provide evaluation context with targeting information.
    """
    
    def __init__(self, provider_options: GrowthBookProviderOptions):
        """Initialize GrowthBook provider with configuration options"""
        self.gb_options = Options(
            api_host=provider_options.api_host,
            client_key=provider_options.client_key,
            decryption_key=provider_options.decryption_key,
            cache_ttl=provider_options.cache_ttl,
            enabled=provider_options.enabled,
            qa_mode=provider_options.qa_mode,
            # on_experiment_viewed=provider_options.on_experiment_viewed,
            sticky_bucket_service=provider_options.sticky_bucket_service
        )
        self.client = None
        self.initialized = False

    async def initialize(self):
        """Initialize the GrowthBook client"""
        self.client = GrowthBookClient(options=self.gb_options)
        self.initialized = await self.client.initialize()

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
        if not self.client or not self.initialized:
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

    def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        """Resolve boolean feature flags"""
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            # Convert OpenFeature context to GrowthBook context
            user_context = self._create_user_context(evaluation_context)
            
            # Get feature result from GrowthBook
            feature_result = run_async(self.client.eval_feature(flag_key, user_context))
            
            # If feature not found, return default
            if not feature_result:
                return FlagResolutionDetails(
                    value=default_value,
                    reason=Reason.DEFAULT
                )
            
            # Map GrowthBook result to OpenFeature result
            return FlagResolutionDetails(
                value=bool(feature_result.value if feature_result.value is not None else default_value),
                variant=feature_result.source.value_type if feature_result.source else None,
                reason=Reason.SPLIT if feature_result.source and feature_result.source.experiment else
                      Reason.TARGETING_MATCH if feature_result.source else
                      Reason.DEFAULT
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            )

    def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        """Resolve string feature flags"""
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = run_async(self.client.get_feature_value(flag_key, default_value, user_context))
            return FlagResolutionDetails(
                value=str(result),
                reason=Reason.TARGETING_MATCH
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            )

    def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        """Resolve integer feature flags"""
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = run_async(self.client.get_feature_value(flag_key, default_value, user_context))
            return FlagResolutionDetails(
                value=int(result),
                reason=Reason.TARGETING_MATCH
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            )

    def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        """Resolve float feature flags"""
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = run_async(self.client.get_feature_value(flag_key, default_value, user_context))
            return FlagResolutionDetails(
                value=float(result),
                reason=Reason.TARGETING_MATCH
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            )

    def resolve_object_details(
        self,
        flag_key: str,
        default_value: Union[dict, list],
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[Union[dict, list]]:
        """Resolve object feature flags"""
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            user_context = self._create_user_context(evaluation_context)
            result = run_async(self.client.get_feature_value(flag_key, default_value, user_context))
            return FlagResolutionDetails(
                value=result,
                reason=Reason.TARGETING_MATCH
            )
        except Exception as e:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            ) 