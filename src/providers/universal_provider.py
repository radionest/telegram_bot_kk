"""Universal AI provider implementation - facade for all providers."""

from typing import Optional, Any

from services.ai.base_ai_client import BaseAiClient
from services.ai.provider_factory import ProviderFactory
from services.ai.provider_adapter import ProviderAdapter
from models.message_history import MessageHistoryStorage
from models.ai_config import AIProviderName
from utils.logger import logger


class UniversalAIProvider(BaseAiClient):
    """Universal AI provider facade that supports multiple backends.

    This provider implements the BaseAiClient interface and delegates
    actual API calls to specific provider implementations.
    """
    
    def __init__(
        self,
        provider: AIProviderName,
        api_key: str,
        model_name: str,
        message_history_storage: Optional[MessageHistoryStorage] = None,
        temperature: float = 0.7,
        **extra_params: Any
    ):
        """Initialize universal provider.

        Args:
            provider: The AI provider type
            api_key: API key for the provider
            model_name: Model name to use
            message_history_storage: Optional storage for conversation history
            temperature: Default temperature for generation
            **extra_params: Additional provider-specific parameters
        """
        super().__init__(message_history_storage, temperature)

        # Create the actual provider using factory
        self.provider_impl = ProviderFactory.create_provider_by_type(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            **extra_params
        )

        self.provider = provider
        self.model_name = model_name

        logger.info(f"Initialized {provider.value} provider with model: {model_name}")
    
    async def check_health(self) -> bool:
        """Check if the provider is healthy.

        Returns:
            True if provider is healthy, False otherwise
        """
        return await self.provider_impl.check_health()

    async def _generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using the configured provider.

        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            APIError: If the API request fails
        """
        return await self.provider_impl.generate_text(prompt, temperature, max_tokens)
