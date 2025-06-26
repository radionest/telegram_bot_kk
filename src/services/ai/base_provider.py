"""Base provider abstract class for AI providers."""

from abc import ABC, abstractmethod
from typing import Optional, Any

from loguru import logger

from models.ai_config import AIProviderName
from exceptions import APIError


class BaseProvider(ABC):
    """Abstract base class for AI provider implementations.
    
    This class defines the interface that all AI providers must implement.
    Unlike BaseAiClient, this class focuses only on the raw API interaction,
    not the business logic.
    """
    
    def __init__(
        self,
        provider: AIProviderName,
        api_key: str,
        model_name: str,
        temperature: float = 0.7,
        **extra_params: Any
    ):
        """Initialize base provider.
        
        Args:
            provider: The AI provider type
            api_key: API key for the provider
            model_name: Model name to use
            temperature: Default temperature for generation
            **extra_params: Additional provider-specific parameters
        """
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.extra_params = extra_params
        
        logger.info(f"Initializing {provider.value} provider with model: {model_name}")
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using the provider's API.
        
        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
        Raises:
            APIError: If the API request fails
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """Check if the provider is healthy and accessible.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
    
    def _handle_api_error(self, error: Exception, context: str = "") -> APIError:
        """Convert provider-specific errors to standardized APIError.
        
        Args:
            error: The original exception
            context: Additional context about where the error occurred
            
        Returns:
            Standardized APIError
        """
        error_msg = f"{self.provider.value} API error"
        if context:
            error_msg += f" during {context}"
        error_msg += f": {str(error)}"
        
        logger.error(error_msg)
        return APIError(error_msg, api_name=self.provider.value)