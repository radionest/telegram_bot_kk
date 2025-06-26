"""Configuration settings for the bot."""

from typing import Dict, Optional
import yaml
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from exceptions import ConfigError
from utils.logger import logger
from models.ai_config import ModelPoolConfig


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
       
    # Model pool configuration
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
    def model_pool_config(self) -> Optional[ModelPoolConfig]:
        """Load and return model pool configuration from YAML file."""
        config_path = Path(self.MODEL_POOL_CONFIG_PATH)
        if not config_path.exists():
            # Try relative to project root
            config_path = Path(__file__).parent.parent.parent / self.MODEL_POOL_CONFIG_PATH
        
        if not config_path.exists():
            logger.warning(f"Model pool config file not found: {self.MODEL_POOL_CONFIG_PATH}")
            # Fall back to legacy configuration
            return self._create_pool_from_env_vars()
        
        try:
            with open(config_path, 'r') as f:
                config_data: ModelPoolConfig = yaml.safe_load(f)
            
            ai_providers = {p.name : p.api_key for p in config_data.providers}
            
            for model_data in config_data.models:
                # Substitute environment variables
                model_data.api_key = model_data.api_key or ai_providers[model_data.provider]    
            return config_data
                
        except Exception as e:
            raise ConfigError(f"Failed to load model pool config: {e}")


# Create settings instance with validation
try:
    settings = Settings()
    # Log configuration at startup
    logger.info("Configuration loaded successfully")
    logger.debug(f"MIN_MESSAGE_LENGTH: {settings.MIN_MESSAGE_LENGTH}")
    logger.debug(f"REACTION_EMOJI: {settings.REACTION_EMOJI}")
except Exception as e:
    raise ConfigError(f"Failed to load configuration: {e}")
