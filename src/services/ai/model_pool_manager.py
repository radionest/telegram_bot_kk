"""Model pool manager for AI clients."""

import random
from typing import List, Optional, Dict

from loguru import logger

from models.ai_config import ModelConfig, ModelPoolConfig, AIProviderName
from models.message_history import MessageHistoryStorage
from services.ai.base_ai_client import BaseAiClient
from services.ai.base_provider import BaseProvider
from services.ai.provider_factory import ProviderFactory


class ModelPoolManager(BaseAiClient):
    """Manages a pool of AI models and handles random selection.
    
    This class extends BaseAiClient to provide a unified interface
    for AI operations while randomly selecting from a pool of models.
    The actual prompt logic is inherited from BaseAiClient.
    """
    
    def __init__(
        self, 
        pool_config: ModelPoolConfig,
        message_history_storage: Optional[MessageHistoryStorage] = None
    ):
        """Initialize model pool manager.
        
        Args:
            pool_config: Configuration for the model pool
            message_history_storage: Optional storage for conversation history
        """
        super().__init__(message_history_storage)
        self.pool_config = pool_config
        self._provider_cache: Dict[tuple, BaseProvider] = {}
        
    def _create_provider(self, model_config: ModelConfig) -> BaseProvider:
        """Create an AI provider for the given model configuration.
        
        Args:
            model_config: Model configuration
            
        Returns:
            AI provider instance
        """
        cache_key = (model_config.provider, model_config.model_name, model_config.api_key)
        
        # Check cache first
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]
        
        # Create new provider using factory
        provider = ProviderFactory.create_provider(model_config)
        
        # Cache the provider
        self._provider_cache[cache_key] = provider
        return provider
    
    def get_random_provider(
        self, 
        allowed_models: Optional[List[str]] = None,
        allowed_providers: Optional[List[AIProviderName]] = None
    ) -> BaseProvider:
        """Get a random AI provider from the pool.
        
        Args:
            allowed_models: List of model names to choose from. If None, all models are allowed.
            allowed_providers: List of providers to choose from. If None, all providers are allowed.
            
        Returns:
            Randomly selected AI provider.
            
        Raises:
            ValueError: If no suitable models are found.
        """
        # Filter models based on criteria
        available_models = self.pool_config.models
        
        if allowed_models:
            available_models = [
                m for m in available_models 
                if m.model_name in allowed_models
            ]
        
        if allowed_providers:
            available_models = [
                m for m in available_models 
                if m.provider in allowed_providers
            ]
        
        if not available_models:
            raise ValueError("No suitable models found in the pool")
        
        # Select random model
        selected_model = random.choice(available_models)
        logger.info(f"Selected model: {selected_model.provider.value}:{selected_model.model_name}")
        
        # Create and return provider
        return self._create_provider(selected_model)
    
    def get_provider_by_type(self, provider: AIProviderName) -> BaseProvider:
        """Get a random provider for a specific provider type.
        
        Args:
            provider: Provider type
            
        Returns:
            Random provider of the specified type
            
        Raises:
            ValueError: If no models found for the provider
        """
        provider_models = self.pool_config.get_models_by_provider(provider)
        if not provider_models:
            raise ValueError(f"No models found for provider: {provider}")
        
        selected_model = random.choice(provider_models)
        return self._create_provider(selected_model)
    
    def get_all_available_models(self) -> List[str]:
        """Get list of all available model names.
        
        Returns:
            List of model identifiers in format "provider:model_name"
        """
        return [f"{m.provider.value}:{m.model_name}" for m in self.pool_config.models]
    
    async def _generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using a random provider from the pool.
        
        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        # Get a random provider
        provider = self.get_random_provider()
        
        # Delegate to the selected provider
        provider_instance = provider
        logger.debug(f"Generating text with provider: {type(provider_instance).__name__}")
        return await provider_instance.generate_text(prompt, temperature, max_tokens)
    
    # The analyze_topic_compliance and generate_free_response methods are inherited
    # from BaseAiClient and will use the _generate_text method defined above
