"""Gemini AI provider implementation."""

from typing import Optional, Any

from google import genai
from google.genai import types
from loguru import logger

from config.settings import settings
from models.ai_config import AIProviderName
from services.ai.base_provider import BaseProvider
from exceptions import APIError


class GeminiProvider(BaseProvider):
    """Gemini-specific AI provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-pro",
        temperature: float = 0.7,
        **extra_params: Any
    ):
        """Initialize Gemini provider.
        
        Args:
            api_key: Gemini API key
            model_name: Model name to use (default: gemini-pro)
            temperature: Default temperature for generation
            **extra_params: Additional Gemini-specific parameters
        """
        super().__init__(
            provider=AIProviderName.GEMINI,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            **extra_params
        )
        
        self._init_client()
    
    def _init_client(self):
        """Initialize Gemini client with optional proxy configuration."""
        if settings.HTTP_PROXY or settings.HTTPS_PROXY:
            proxy_url = settings.HTTPS_PROXY or settings.HTTP_PROXY
            http_options = types.HttpOptions(
                client_args={'proxy': proxy_url},
                async_client_args={'proxy': proxy_url}
            )
            self.client = genai.Client(api_key=self.api_key, http_options=http_options)
            logger.debug(f"Initialized Gemini client with proxy: {proxy_url}")
        else:
            self.client = genai.Client(api_key=self.api_key)
            logger.debug("Initialized Gemini client without proxy")
    
    async def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using Gemini API.
        
        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
        Raises:
            APIError: If the API request fails
        """
        try:
            config = types.GenerateContentConfig(
                temperature=temperature or self.temperature,
                top_p=self.extra_params.get('top_p', 0.95),
                top_k=self.extra_params.get('top_k', 40),
            )
            
            if max_tokens:
                config.max_output_tokens = max_tokens
            
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            if not response or not response.text:
                raise APIError("Empty response from Gemini API", api_name="Gemini")
            
            return response.text
            
        except Exception as e:
            raise self._handle_api_error(e, "text generation")
    
    async def check_health(self) -> bool:
        """Check if Gemini API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple test generation
            await self.generate_text("Hello", temperature=0.1, max_tokens=10)
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False