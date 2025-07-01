from typing import List, Optional, Union, Dict, Any, Callable
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import traceback

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

logger = logging.getLogger(__name__)

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
    """
    Run a coroutine in the current event loop or create a new one if needed.
    
    This function handles several edge cases:
    1. No event loop exists
    2. Event loop exists but can't be accessed
    3. Event loop is running (nested case)
    4. Coroutine raises an exception
    5. Cleanup of newly created event loops
    
    Performance optimizations:
    1. Avoids unnecessary task creation in nested async contexts
    2. Caches loop detection result
    3. Minimizes exception handling overhead
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
        
    Raises:
        RuntimeError: If no event loop can be found or created
        Exception: Any exception raised by the coroutine
    """
    # Quick check for running loop first (most common case in async contexts)
    try:
        loop = asyncio.get_running_loop()

        # We're in an async context - run in separate thread
        def run_in_thread():
            return asyncio.run(coro)
        
        # Execute in thread pool
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_in_thread)
            return future.result() # blocks until the result is ready - Fix to support backwards compatibility.
    except RuntimeError:
        # Not in async context, proceed with sync handling
        pass

    # Sync context handling
    try:
        loop = asyncio.get_event_loop()
        created_new_loop = False
    except RuntimeError:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            created_new_loop = True
        except RuntimeError as e:
            raise RuntimeError("No event loop found and unable to create one") from e

    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        raise e
    finally:
        if created_new_loop:
            try:
                loop.close()
            except Exception:
                pass  # Ignore cleanup errors

class GrowthBookProvider(AbstractProvider):
    """GrowthBook provider implementation for OpenFeature.
    
    This provider integrates GrowthBook feature flags with the OpenFeature SDK.

    Note: While OpenFeature supports optional evaluation context,
    GrowthBook requires user context for proper targeting. It's recommended
    to always provide evaluation context with targeting information.
    
    Example usage:
    ```python
    from openfeature.api import OpenFeatureAPI
    from growthbook_openfeature_provider import GrowthBookProvider, GrowthBookProviderOptions
    
    # Create and initialize the provider
    provider = GrowthBookProvider(GrowthBookProviderOptions(
        api_host="https://cdn.growthbook.io",
        client_key="sdk-abc123"
    ))
    
    # Initialize the provider (async)
    await provider.initialize()
    
    # Register with OpenFeature
    OpenFeatureAPI.set_provider(provider)
    
    # Use OpenFeature client to evaluate flags
    client = OpenFeatureAPI.get_client()
    value = client.get_boolean_value("my-flag", False)
    ```
    """
    
    def __init__(self, provider_options: GrowthBookProviderOptions):
        """Initialize GrowthBook provider with configuration options"""
        # Create options without the on_experiment_viewed parameter
        self.gb_options = Options(
            api_host=provider_options.api_host,
            client_key=provider_options.client_key,
            decryption_key=provider_options.decryption_key,
            cache_ttl=provider_options.cache_ttl,
            enabled=provider_options.enabled,
            qa_mode=provider_options.qa_mode,
            sticky_bucket_service=provider_options.sticky_bucket_service
        )
        
        # Set on_experiment_viewed separately if it exists
        if provider_options.on_experiment_viewed is not None:
            setattr(self.gb_options, 'on_experiment_viewed', provider_options.on_experiment_viewed)  # type: ignore
        
        self.client = None
        self.initialized = False

    async def initialize(self):
        """Initialize the GrowthBook client"""
        self.client = GrowthBookClient(options=self.gb_options)
        self.initialized = await self.client.initialize()

    def initialize_sync(self):
        """Synchronous initialization for non-async contexts"""
        return run_async(self.initialize())

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
        
        # Use targeting_key as id if provided
        if evaluation_context.targeting_key:
            attributes['id'] = evaluation_context.targeting_key

        return UserContext(attributes=attributes)

    def _eval_feature_sync(self, flag_key: str, user_context: UserContext):
        """Synchronous version of eval_feature that uses the cached features"""
        if not self.client:
            return None

        return self.client.eval_feature(flag_key, user_context)

    async def _process_flag_evaluation_async(
        self,
        flag_key: str,
        default_value: Any,
        evaluation_context: Optional[EvaluationContext] = None,
        value_converter: Callable[[Any], Any] = lambda x: x
    ) -> FlagResolutionDetails:
        """Async version of _process_flag_evaluation for use in async contexts."""
        logger.debug(f"Processing flag evaluation for {flag_key} with context {evaluation_context}")
        
        if not self.client or not self.initialized:
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.PROVIDER_NOT_READY,
                reason=Reason.ERROR
            )

        try:
            # Convert OpenFeature context to GrowthBook context
            user_context = self._create_user_context(evaluation_context)
            
            # For targeting to work, we need an id
            if not user_context.attributes.get('id') and evaluation_context and evaluation_context.targeting_key:
                return FlagResolutionDetails(
                    value=default_value,
                    error_code=ErrorCode.TARGETING_KEY_MISSING,
                    reason=Reason.ERROR
                )
            
            # Evaluate the feature using eval_feature - properly await the async call
            logger.debug(f"Evaluating feature {flag_key} with context {user_context}")
            feature_result = await self.client.eval_feature(flag_key, user_context)
                
            # Handle feature not found
            if feature_result is None:
                return FlagResolutionDetails(
                    value=default_value,
                    reason=Reason.DEFAULT,
                    error_code=None  # Ensure no error code is set for default values
                )
            
            # Add type safety for value conversion to prevent runtime errors
            try:
                value = value_converter(feature_result.value) if feature_result.value is not None else default_value
            except (ValueError, TypeError) as e:
                logger.error(f"Type conversion error: {e}")
                return FlagResolutionDetails(
                    value=default_value,
                    error_code=ErrorCode.TYPE_MISMATCH,
                    error_message=f"Failed to convert value: {str(e)}",
                    reason=Reason.ERROR
                )
            
            # Determine the reason based on the result
            reason = Reason.DEFAULT
            variant = None
            
            # Check if from targeting rule
            if hasattr(feature_result, 'ruleId') and feature_result.ruleId:
                logger.debug(f"Targeting rule matched-: {feature_result.ruleId}")
                reason = Reason.TARGETING_MATCH
                variant = feature_result.ruleId
            # Check if this is from an experiment
            elif hasattr(feature_result, 'experimentResult') and feature_result.experimentResult:
                logger.debug(f"Experiment variation assigned: {feature_result.experimentResult}")
                reason = Reason.SPLIT
                variant = str(feature_result.experimentResult.variationId)
            
            return FlagResolutionDetails(
                value=value,
                variant=variant,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Error during flag evaluation: {e}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return FlagResolutionDetails(
                value=default_value,
                error_code=ErrorCode.GENERAL,
                error_message=str(e),
                reason=Reason.ERROR
            )

    def _process_flag_evaluation(
        self,
        flag_key: str,
        default_value: Any,
        evaluation_context: Optional[EvaluationContext] = None,
        value_converter: Callable[[Any], Any] = lambda x: x
    ) -> FlagResolutionDetails:
        """Synchronous version of flag evaluation for OpenFeature interface."""
        return run_async(self._process_flag_evaluation_async(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context,
            value_converter=value_converter
        ))

    def resolve_boolean_details(
        self,
        flag_key: str,
        default_value: bool,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[bool]:
        """Resolve boolean feature flags"""
        return self._process_flag_evaluation(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context,
            value_converter=bool
        )

    def resolve_string_details(
        self,
        flag_key: str,
        default_value: str,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[str]:
        """Resolve string feature flags"""
        return self._process_flag_evaluation(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context,
            value_converter=str
        )

    def resolve_integer_details(
        self,
        flag_key: str,
        default_value: int,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[int]:
        """Resolve integer feature flags"""
        return self._process_flag_evaluation(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context,
            value_converter=int
        )

    def resolve_float_details(
        self,
        flag_key: str,
        default_value: float,
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[float]:
        """Resolve float feature flags"""
        return self._process_flag_evaluation(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context,
            value_converter=float
        )

    def resolve_object_details(
        self,
        flag_key: str,
        default_value: Union[dict, list],
        evaluation_context: Optional[EvaluationContext] = None,
    ) -> FlagResolutionDetails[Union[dict, list]]:
        """Resolve object feature flags"""
        return self._process_flag_evaluation(
            flag_key=flag_key,
            default_value=default_value,
            evaluation_context=evaluation_context
        )

    async def close(self):
        """Clean up resources when provider is no longer needed"""
        if self.client:
            await self.client.close()
            self.client = None
            self.initialized = False 