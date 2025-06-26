"""Factory for creating AI providers."""

from typing import Dict, Type, Any, Optional, List

from loguru import logger

from models.ai_config import AIProviderName, ModelConfig
from services.ai.base_provider import BaseProvider
from providers.gemini_provider import GeminiProvider
from providers.groq_provider import GroqProvider
from exceptions import ConfigError


class ProviderFactory:
    """Factory for creating AI provider instances."""
    
    # Registry of provider implementations
    _providers: Dict[AIProviderName, Type[BaseProvider]] = {
        AIProviderName.GEMINI: GeminiProvider,
        AIProviderName.GROQ: GroqProvider,
    }
    
    @classmethod
    def register_provider(cls, provider: AIProviderName, provider_class: Type[BaseProvider]):
        """Register a new provider implementation.
        
        Args:
            provider: Provider enum value
            provider_class: Provider implementation class
        """
        cls._providers[provider] = provider_class
        logger.info(f"Registered provider: {provider.value}")
    
    @classmethod
    def create_provider(cls, config: ModelConfig) -> BaseProvider:
        """Create a provider instance from configuration.
        
        Args:
            config: Model configuration
            
        Returns:
            Provider instance
            
        Raises:
            ConfigError: If provider is not supported
        """
        provider_class = cls._providers.get(config.provider)
        if not provider_class:
            raise ConfigError(
                f"Unsupported provider: {config.provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )
        
        # Extract provider-specific parameters
        kwargs: Dict[str, Any] = {
            "api_key": config.api_key,
            "model_name": config.model_name,
            "temperature": config.temperature,
        }
        
        # Add extra parameters
        kwargs.update(config.extra_params)
        
        # Create and return provider instance
        return provider_class(**kwargs)
    
    @classmethod
    def create_provider_by_type(
        cls,
        provider: AIProviderName,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        **extra_params: Any
    ) -> BaseProvider:
        """Create a provider instance by type.
        
        Args:
            provider: Provider type
            api_key: API key
            model_name: Model name
            temperature: Default temperature
            **extra_params: Additional parameters
            
        Returns:
            Provider instance
        """
        config = ModelConfig(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            extra_params=extra_params
        )
        
        return cls.create_provider(config)
    
    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """Get list of supported provider names.
        
        Returns:
            List of provider names
        """
        return [p.value for p in cls._providers.keys()]