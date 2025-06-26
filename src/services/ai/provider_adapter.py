"""Adapter to use BaseProvider implementations with BaseAiClient interface."""

from typing import Optional

from models.message_history import MessageHistoryStorage
from services.ai.base_ai_client import BaseAiClient
from services.ai.base_provider import BaseProvider


class ProviderAdapter(BaseAiClient):
    """Adapter that wraps a BaseProvider to work with BaseAiClient interface.
    
    This adapter allows using the new provider architecture while maintaining
    compatibility with existing code that expects BaseAiClient interface.
    """
    
    def __init__(
        self,
        provider: BaseProvider,
        message_history_storage: Optional[MessageHistoryStorage] = None,
        temperature: float = 0.7,
    ):
        """Initialize provider adapter.
        
        Args:
            provider: The AI provider instance
            message_history_storage: Optional storage for conversation history
            temperature: Default temperature for text generation
        """
        super().__init__(message_history_storage, temperature)
        self.provider = provider
    
    async def _generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using the wrapped provider.
        
        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        return await self.provider.generate_text(prompt, temperature, max_tokens)