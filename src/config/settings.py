"""Configuration settings for the bot."""

from typing import Dict, List, Optional
import os
import yaml
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from exceptions import ConfigError
from utils.logger import logger
from models.ai_config import ModelConfig, ModelPoolConfig, AIProvider


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Telegram configuration
    TELEGRAM_BOT_TOKEN: str
    
    # Superuser configuration
    SUPERUSER_ID: int
    
    # Legacy configuration for backward compatibility
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash-001"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AI_PROVIDER: str = "gemini"  # "gemini" or "groq"
    
    # Model pool configuration
    USE_MODEL_POOL: bool = False  # Enable model pool feature
    MODEL_POOL_CONFIG_PATH: str = "models.yaml"  # Path to model pool config file
    
    # Proxy configuration (optional)
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""
    
    # Optional configuration with defaults
    VIOLATION_TIME_WINDOW: int = 60
    VIOLATION_MAX_LENGTH: int = 10
    RESET_ON_TOPIC_MOVE: bool = True
    MIN_MESSAGE_LENGTH: int = 10
    REACTION_EMOJI: str = "👾"
    RANDOM_REPLY_PROBABILITY: float = 0.03
    
    # Static configuration - topics and reaction levels
    @property
    def chat_topics(self) -> Dict[str, str]:
        """Chat topics configuration."""
        return {
            "Основной чат": "Общие вопросы и обсуждения без специфической тематики. В этой ветке может обсуждаться все тоже что и в других, кроме БП и шмоток.",
            "Рейт": """
            Резервирование очереди в рейтинговых партиях на ладдере ири на арене (Например: Кто на арене? Я дальше арену). 
            Сбор команды для командной игры (Например: Идём конечно!, ). 
            Обсуждение тактики на предстоящую игру. 
            Обсуждение первых результатов рейтинговой игры. 
            Возможно обсуждение подключения к игре (Например: Моргнуло!, Бля за 2 секунды!, У меня зависло.) 
            """,
            "Шмотки": "Обсуждение вещей, сэтов",
            "Стикеры": "Просьбы о помощи, поддержка участников",
            "Какой БП": """
            Обсуждение боевого пропуска (БП). 
            Сколько очков БП набрано, сколько осталось набрать. Сроки по его закрытию.
            Шмотки которые выпали в БП.
            """,
            "Билды": "Обсуждения и видео билдов",
            "Записи игр": "Записи игр и скирншоты интересных партий"
            
        }
    
    @property
    def reaction_levels(self) -> Dict[int, str]:
        """Reaction intensity configuration."""
        return {
            1: "reaction_only",
            2: "reaction_only", 
            3: "reaction_only",
            4: "reaction_only",
            5: "reaction_only",
            6: "reaction_only",
            7: "reaction_only",
        }
    
    @property
    def analyze_keywords(self) -> List[str]:
        """Keywords for message analysis."""
        return ["вопрос", "помоги", "объясни", "что такое", "как", "почему", "?"]
    
    @property
    def model_pool_config(self) -> Optional[ModelPoolConfig]:
        """Load and return model pool configuration from YAML file."""
        if not self.USE_MODEL_POOL:
            return None
        
        config_path = Path(self.MODEL_POOL_CONFIG_PATH)
        if not config_path.exists():
            # Try relative to project root
            config_path = Path(__file__).parent.parent.parent / self.MODEL_POOL_CONFIG_PATH
        
        if not config_path.exists():
            logger.warning(f"Model pool config file not found: {self.MODEL_POOL_CONFIG_PATH}")
            # Fall back to legacy configuration
            return self._create_legacy_pool_config()
        
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            models = []
            for model_data in config_data.get('models', []):
                # Substitute environment variables
                api_key = model_data['api_key']
                if api_key.startswith('${') and api_key.endswith('}'):
                    env_var = api_key[2:-1]
                    api_key = os.getenv(env_var, '')
                    if not api_key:
                        logger.warning(f"Environment variable {env_var} not set, skipping model")
                        continue
                
                models.append(ModelConfig(
                    provider=AIProvider(model_data['provider']),
                    model_name=model_data['model_name'],
                    api_key=api_key,
                    temperature=model_data.get('temperature', 0.7),
                    max_tokens=model_data.get('max_tokens'),
                    extra_params=model_data.get('extra_params', {})
                ))
            
            if models:
                return ModelPoolConfig(models=models)
            else:
                logger.warning("No valid models found in config file")
                return self._create_legacy_pool_config()
                
        except Exception as e:
            logger.error(f"Failed to load model pool config: {e}")
            return self._create_legacy_pool_config()
    
    def _create_legacy_pool_config(self) -> Optional[ModelPoolConfig]:
        """Create model pool from legacy configuration."""
        models = []
        if self.GEMINI_API_KEY:
            models.append(ModelConfig(
                provider=AIProvider.GEMINI,
                model_name=self.GEMINI_MODEL,
                api_key=self.GEMINI_API_KEY,
                temperature=0.7
            ))
        if self.GROQ_API_KEY:
            models.append(ModelConfig(
                provider=AIProvider.GROQ,
                model_name=self.GROQ_MODEL,
                api_key=self.GROQ_API_KEY,
                temperature=0.7
            ))
        
        return ModelPoolConfig(models=models) if models else None


# Create settings instance with validation
try:
    settings = Settings()
    # Log configuration at startup
    logger.info("Configuration loaded successfully")
    logger.debug(f"MIN_MESSAGE_LENGTH: {settings.MIN_MESSAGE_LENGTH}")
    logger.debug(f"REACTION_EMOJI: {settings.REACTION_EMOJI}")
except Exception as e:
    raise ConfigError(f"Failed to load configuration: {e}")
