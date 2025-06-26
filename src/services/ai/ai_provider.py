"""Protocol for AI model providers."""

from typing import Protocol, Dict, Any, Optional


class AiProvider(Protocol):
    """Protocol defining the interface for AI model providers.
    
    This protocol defines the low-level interface that AI providers
    (Gemini, Groq, OpenAI, etc.) must implement. It focuses solely on
    text generation without any prompt logic.
    """
    
    async def generate_text(
        self, 
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any
    ) -> str:
        """Generate text based on the given prompt.
        
        Args:
            prompt: The input prompt for text generation
            temperature: Controls randomness in generation (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            APIError: If the API request fails
        """
        ...