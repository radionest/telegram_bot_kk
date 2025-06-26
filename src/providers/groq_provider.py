"""Groq AI provider implementation."""

from typing import Optional, Any, List, Dict

from groq import AsyncGroq
from loguru import logger

from config.settings import settings
from models.ai_config import AIProviderName
from services.ai.base_provider import BaseProvider
from exceptions import APIError


class GroqProvider(BaseProvider):
    """Groq-specific AI provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "mixtral-8x7b-32768",
        temperature: float = 0.7,
        **extra_params: Any
    ):
        """Initialize Groq provider.
        
        Args:
            api_key: Groq API key
            model_name: Model name to use (default: mixtral-8x7b-32768)
            temperature: Default temperature for generation
            **extra_params: Additional Groq-specific parameters
        """
        super().__init__(
            provider=AIProviderName.GROQ,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            **extra_params
        )
        
        self._init_client()
    
    def _init_client(self):
        """Initialize Groq client with optional proxy configuration."""
        proxy_config = {}
        if settings.HTTP_PROXY or settings.HTTPS_PROXY:
            proxy_url = settings.HTTPS_PROXY or settings.HTTP_PROXY
            proxy_config = {
                "http": proxy_url,
                "https": proxy_url,
            }
            logger.debug(f"Initialized Groq client with proxy: {proxy_url}")
        
        self.client = AsyncGroq(
            api_key=self.api_key,
            proxies=proxy_config if proxy_config else None
        )
    
    async def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using Groq API.
        
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
            messages = self._prepare_messages(prompt)
            
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "top_p": self.extra_params.get('top_p', 1.0),
                "stream": False,
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            completion = await self.client.chat.completions.create(**kwargs)
            
            if not completion.choices or not completion.choices[0].message.content:
                raise APIError("Empty response from Groq API", api_name="Groq")
            
            return completion.choices[0].message.content
            
        except Exception as e:
            raise self._handle_api_error(e, "text generation")
    
    def _prepare_messages(self, prompt: str) -> List[Dict[str, str]]:
        """Prepare messages in the format expected by Groq API.
        
        Args:
            prompt: The user prompt
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Add system message if provided in extra_params
        if system_prompt := self.extra_params.get('system_prompt'):
            messages.append({"role": "system", "content": system_prompt})
        
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    async def check_health(self) -> bool:
        """Check if Groq API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple test generation
            await self.generate_text("Hello", temperature=0.1, max_tokens=10)
            return True
        except Exception as e:
            logger.warning(f"Groq health check failed: {e}")
            return False