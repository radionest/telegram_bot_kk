"""Configuration settings for the bot."""

from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict

from exceptions import ConfigError
from utils.logger import logger


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # Telegram configuration
    TELEGRAM_BOT_TOKEN: str

    # Superuser configuration
    SUPERUSER_ID: int

    # LiteLLM configuration
    LITELLM_CONFIG_PATH: str = "litellm_models.yaml"
    LITELLM_ROUTER_STRATEGY: str = (
        "round_robin"  # Options: round_robin, priority, random, load_balance
    )

    # Proxy configuration (optional)
    AI_HTTP_PROXY: str = ""
    AI_HTTPS_PROXY: str = ""

    # ChromaDB configuration
    CHROMA_EMBEDDING_MODEL: str = "ai-forever/FRIDA"
    CHROMA_COLLECTION_NAME: str = "telegram_messages"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8700

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
            "Записи игр": "Записи игр и скирншоты интересных партий",
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
    settings = Settings()  # type: ignore[call-arg]
    # Log configuration at startup
    logger.info("Configuration loaded successfully")
    logger.debug(f"MIN_MESSAGE_LENGTH: {settings.MIN_MESSAGE_LENGTH}")
    logger.debug(f"REACTION_EMOJI: {settings.REACTION_EMOJI}")
    logger.debug(f"LITELLM_CONFIG_PATH: {settings.LITELLM_CONFIG_PATH}")
    logger.debug(f"LITELLM_ROUTER_STRATEGY: {settings.LITELLM_ROUTER_STRATEGY}")
except Exception as e:
    raise ConfigError(f"Failed to load configuration: {e}")
