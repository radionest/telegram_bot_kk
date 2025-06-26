"""AI services module for the bot."""

from .base_ai_client import BaseAiClient
from .base_provider import BaseProvider
from .provider_factory import ProviderFactory
from .provider_adapter import ProviderAdapter
from .model_pool_manager import ModelPoolManager
from .protocols import (
    AIProviderProtocol,
    TopicAnalyzerProtocol,
    ConversationalAIProtocol,
    ModelSelectorProtocol
)

__all__ = [
    # Base classes
    'BaseAiClient',
    'BaseProvider',
    
    # Factory and utilities
    'ProviderFactory',
    'ProviderAdapter',
    'ModelPoolManager',
    
    # Protocols
    'AIProviderProtocol',
    'TopicAnalyzerProtocol',
    'ConversationalAIProtocol',
    'ModelSelectorProtocol',
]