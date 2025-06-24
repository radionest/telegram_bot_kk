from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class AIProvider(str, Enum):
    """Supported AI providers"""
    GEMINI = "gemini"
    GROQ = "groq"
    OPENAI = "openai"
    CLAUDE = "claude"


@dataclass
class ModelConfig:
    """Configuration for a single AI model"""
    provider: AIProvider
    model_name: str
    api_key: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.api_key:
            raise ValueError(f"API key is required for {self.provider} model {self.model_name}")


@dataclass 
class ModelPoolConfig:
    """Configuration for a pool of AI models"""
    models: List[ModelConfig]
    
    def __post_init__(self):
        if not self.models:
            raise ValueError("Model pool must contain at least one model")
        
        # Validate that all models have unique identifiers
        model_ids = [(m.provider, m.model_name, m.api_key) for m in self.models]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("Model pool contains duplicate model configurations")
    
    def get_models_by_provider(self, provider: AIProvider) -> List[ModelConfig]:
        """Get all models for a specific provider"""
        return [m for m in self.models if m.provider == provider]
    
    def get_models_by_api_key(self, api_key: str) -> List[ModelConfig]:
        """Get all models using a specific API key"""
        return [m for m in self.models if m.api_key == api_key]