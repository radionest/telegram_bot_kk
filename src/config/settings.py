"""Configuration settings for the bot."""

from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict

from exceptions import ConfigError
from utils.logger import logger


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
    
    # Gemini configuration
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemma-3n-e4b-it"
    
    # Groq configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # AI provider selection
    AI_PROVIDER: str = "gemini"  # "gemini" or "groq"
    
    # Optional configuration with defaults
    VIOLATION_TIME_WINDOW: int = 60
    VIOLATION_MAX_LENGTH: int = 10
    RESET_ON_TOPIC_MOVE: bool = True
    MIN_MESSAGE_LENGTH: int = 10
    REACTION_EMOJI: str = "👾"
    
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


# Create settings instance with validation
try:
    settings = Settings()
    # Log configuration at startup
    logger.info("Configuration loaded successfully")
    logger.debug(f"MIN_MESSAGE_LENGTH: {settings.MIN_MESSAGE_LENGTH}")
    logger.debug(f"REACTION_EMOJI: {settings.REACTION_EMOJI}")
except Exception as e:
    raise ConfigError(f"Failed to load configuration: {e}")
