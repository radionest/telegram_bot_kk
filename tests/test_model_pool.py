import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.ai_config import ModelConfig, ModelPoolConfig, AIProvider
from services.model_pool_manager import ModelPoolManager
from models.analysis import TopicAnalysisRequest, TopicAnalysisResult


@pytest.fixture
def model_pool_config():
    """Create test model pool configuration."""
    models = [
        ModelConfig(
            provider=AIProvider.GEMINI,
            model_name="gemini-1.5-pro",
            api_key="test_key_1",
            temperature=0.7
        ),
        ModelConfig(
            provider=AIProvider.GEMINI,
            model_name="gemini-2.0-flash",
            api_key="test_key_2",
            temperature=0.5
        ),
        ModelConfig(
            provider=AIProvider.GROQ,
            model_name="llama-3.3-70b",
            api_key="test_key_3",
            temperature=0.7
        ),
    ]
    return ModelPoolConfig(models=models)


@pytest.fixture
def model_pool_manager(model_pool_config):
    """Create test model pool manager."""
    return ModelPoolManager(pool_config=model_pool_config)


def test_model_pool_config_creation():
    """Test creating model pool configuration."""
    models = [
        ModelConfig(
            provider=AIProvider.GEMINI,
            model_name="test-model",
            api_key="test-key",
            temperature=0.5
        )
    ]
    config = ModelPoolConfig(models=models)
    assert len(config.models) == 1
    assert config.models[0].provider == AIProvider.GEMINI


def test_model_pool_config_validation():
    """Test model pool configuration validation."""
    # Empty models list should raise error
    with pytest.raises(ValueError, match="Model pool must contain at least one model"):
        ModelPoolConfig(models=[])
    
    # Duplicate models should raise error
    models = [
        ModelConfig(provider=AIProvider.GEMINI, model_name="test", api_key="key1"),
        ModelConfig(provider=AIProvider.GEMINI, model_name="test", api_key="key1"),
    ]
    with pytest.raises(ValueError, match="duplicate model configurations"):
        ModelPoolConfig(models=models)


def test_get_models_by_provider(model_pool_config):
    """Test filtering models by provider."""
    gemini_models = model_pool_config.get_models_by_provider(AIProvider.GEMINI)
    assert len(gemini_models) == 2
    assert all(m.provider == AIProvider.GEMINI for m in gemini_models)
    
    groq_models = model_pool_config.get_models_by_provider(AIProvider.GROQ)
    assert len(groq_models) == 1
    assert groq_models[0].provider == AIProvider.GROQ


def test_get_models_by_api_key(model_pool_config):
    """Test filtering models by API key."""
    models = model_pool_config.get_models_by_api_key("test_key_1")
    assert len(models) == 1
    assert models[0].api_key == "test_key_1"


def test_get_random_client(model_pool_manager):
    """Test getting random client from pool."""
    # Mock client creation
    model_pool_manager._create_client = MagicMock()
    
    # Get random client without filters
    client = model_pool_manager.get_random_client()
    assert model_pool_manager._create_client.called
    
    # Verify a model was selected
    selected_model = model_pool_manager._create_client.call_args[0][0]
    assert selected_model in model_pool_manager.pool_config.models


def test_get_random_client_with_filters(model_pool_manager):
    """Test getting random client with filters."""
    model_pool_manager._create_client = MagicMock()
    
    # Filter by provider
    client = model_pool_manager.get_random_client(allowed_providers=[AIProvider.GROQ])
    selected_model = model_pool_manager._create_client.call_args[0][0]
    assert selected_model.provider == AIProvider.GROQ
    
    # Filter by model name
    client = model_pool_manager.get_random_client(allowed_models=["gemini-1.5-pro"])
    selected_model = model_pool_manager._create_client.call_args[0][0]
    assert selected_model.model_name == "gemini-1.5-pro"


def test_get_random_client_no_suitable_models(model_pool_manager):
    """Test error when no suitable models found."""
    with pytest.raises(ValueError, match="No suitable models found"):
        model_pool_manager.get_random_client(allowed_providers=[AIProvider.OPENAI])


def test_client_caching(model_pool_manager):
    """Test that clients are cached properly."""
    model_pool_manager._create_client = MagicMock()
    
    # Get same model twice
    model = model_pool_manager.pool_config.models[0]
    cache_key = (model.provider, model.model_name, model.api_key)
    
    # Manually create client and add to cache
    mock_client = MagicMock()
    model_pool_manager._client_cache[cache_key] = mock_client
    
    # Request client for same model - should use cache
    model_pool_manager._create_client = MagicMock(return_value=mock_client)
    client = model_pool_manager._create_client(model)
    
    # Verify we got the cached client
    assert client == mock_client


def test_get_all_available_models(model_pool_manager):
    """Test listing all available models."""
    models = model_pool_manager.get_all_available_models()
    assert len(models) == 3
    assert "gemini:gemini-1.5-pro" in models
    assert "gemini:gemini-2.0-flash" in models
    assert "groq:llama-3.3-70b" in models


@pytest.mark.asyncio
async def test_integration_with_response_manager():
    """Test integration with response manager."""
    from services.response_manager import ResponseManager
    from services.chat_manager import ChatManager
    
    # Create mocks
    bot = AsyncMock()
    ai_client = AsyncMock()
    chat_manager = ChatManager(bot, ai_client)
    
    # Create model pool
    models = [
        ModelConfig(provider=AIProvider.GEMINI, model_name="test", api_key="key1"),
    ]
    pool_config = ModelPoolConfig(models=models)
    model_pool_manager = ModelPoolManager(pool_config)
    
    # Mock client creation
    mock_client = AsyncMock()
    mock_client.generate_free_response.return_value = "Test response"
    model_pool_manager._create_client = MagicMock(return_value=mock_client)
    
    # Create response manager with model pool
    response_manager = ResponseManager(bot, chat_manager, model_pool_manager)
    
    # Test AI response generation
    response = await response_manager.generate_ai_response(
        message="Test message",
        chat_id=123,
        topic_id=456
    )
    
    assert response == "Test response"
    mock_client.generate_free_response.assert_called_once_with("Test message", 123, 456)