"""Protocol definitions for AI services."""

from typing import Protocol, Optional, runtime_checkable
from abc import abstractmethod

from models.analysis import TopicAnalysisRequest, TopicAnalysisResult


@runtime_checkable
class AIProviderProtocol(Protocol):
    """Protocol for AI provider implementations."""
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using the AI provider.
        
        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
        Raises:
            APIError: If the API request fails
        """
        ...


@runtime_checkable  
class TopicAnalyzerProtocol(Protocol):
    """Protocol for topic analysis functionality."""
    
    @abstractmethod
    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult:
        """Analyze if a message is appropriate for its topic.
        
        Args:
            request: Topic analysis request with message and topic details
            
        Returns:
            Topic analysis result with compliance assessment
            
        Raises:
            APIError: If API request fails
        """
        ...


@runtime_checkable
class ConversationalAIProtocol(Protocol):
    """Protocol for conversational AI functionality."""
    
    @abstractmethod
    async def generate_free_response(
        self, 
        message: str, 
        chat_id: int, 
        topic_id: Optional[int] = None
    ) -> str:
        """Generate a free-form response to a message.
        
        Args:
            message: The user's message
            chat_id: The chat ID for context
            topic_id: Optional topic ID for conversation context
            
        Returns:
            Generated response
        """
        ...


@runtime_checkable
class ModelSelectorProtocol(Protocol):
    """Protocol for model selection strategies."""
    
    @abstractmethod
    def select_model(self) -> AIProviderProtocol:
        """Select an AI model based on the implementation strategy.
        
        Returns:
            Selected AI provider instance
        """
        ...