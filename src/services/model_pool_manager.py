import random
from typing import List, Optional, Dict, Protocol
from loguru import logger

from models.ai_config import ModelConfig, ModelPoolConfig, AIProvider
from services.ai_client import AiClient
from utils.gemini_client import GeminiClient
from utils.groq_client import GroqClient
from models.message_history import MessageHistoryStorage
from models.analysis import TopicAnalysisRequest, TopicAnalysisResult


class ModelPoolManager:
    """Manages a pool of AI models and handles random selection.
    
    This class implements the AiClient protocol to provide a unified interface
    for AI operations while randomly selecting from a pool of models.
    """
    
    def __init__(
        self, 
        pool_config: ModelPoolConfig,
        message_history_storage: Optional[MessageHistoryStorage] = None
    ):
        self.pool_config = pool_config
        self.message_history_storage = message_history_storage
        self._client_cache: Dict[tuple, AiClient] = {}
        
    def _create_client(self, model_config: ModelConfig) -> AiClient:
        """Create an AI client for the given model configuration."""
        cache_key = (model_config.provider, model_config.model_name, model_config.api_key)
        
        # Check cache first
        if cache_key in self._client_cache:
            return self._client_cache[cache_key]
        
        # Create new client based on provider
        if model_config.provider == AIProvider.GEMINI:
            client = GeminiClient(
                api_key=model_config.api_key,
                model_name=model_config.model_name,
                temperature=model_config.temperature,
                message_history_storage=self.message_history_storage
            )
        elif model_config.provider == AIProvider.GROQ:
            client = GroqClient(
                api_key=model_config.api_key,
                model_name=model_config.model_name,
                temperature=model_config.temperature,
                message_history_storage=self.message_history_storage
            )
        else:
            raise ValueError(f"Unsupported provider: {model_config.provider}")
        
        # Cache the client
        self._client_cache[cache_key] = client
        return client
    
    def get_random_client(
        self, 
        allowed_models: Optional[List[str]] = None,
        allowed_providers: Optional[List[AIProvider]] = None
    ) -> AiClient:
        """Get a random AI client from the pool.
        
        Args:
            allowed_models: List of model names to choose from. If None, all models are allowed.
            allowed_providers: List of providers to choose from. If None, all providers are allowed.
            
        Returns:
            Randomly selected AI client.
            
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
        logger.info(f"Selected model: {selected_model.provider}:{selected_model.model_name}")
        
        # Create and return client
        return self._create_client(selected_model)
    
    def get_client_by_provider(self, provider: AIProvider) -> AiClient:
        """Get a random client for a specific provider."""
        provider_models = self.pool_config.get_models_by_provider(provider)
        if not provider_models:
            raise ValueError(f"No models found for provider: {provider}")
        
        selected_model = random.choice(provider_models)
        return self._create_client(selected_model)
    
    def get_all_available_models(self) -> List[str]:
        """Get list of all available model names."""
        return [f"{m.provider}:{m.model_name}" for m in self.pool_config.models]
    
    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult:
        """Analyze if a message complies with topic requirements using a random model.
        
        Args:
            request: The analysis request containing message and topic details
            
        Returns:
            Analysis result with compliance decision and confidence score
        """
        # Get a random client from the pool
        client = self.get_random_client()
        
        # Delegate to the selected client
        logger.info(f"Analyzing topic compliance with {type(client).__name__}")
        return await client.analyze_topic_compliance(request)
    
    async def generate_free_response(
        self, message: str, chat_id: int, topic_id: Optional[int] = None
    ) -> str:
        """Generate a free-form response to a message using a random model.
        
        Args:
            message: The user's message
            chat_id: The chat ID for context
            topic_id: Optional topic ID for conversation context
            
        Returns:
            Generated response
        """
        # Get a random client from the pool
        client = self.get_random_client()
        
        # Delegate to the selected client
        logger.info(f"Generating free response with {type(client).__name__}")
        return await client.generate_free_response(message, chat_id, topic_id)