"""Response management service for bot reactions and messages."""

from typing import Optional, List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from config.settings import settings
from services.chat_manager import ChatManager
from services.ai.model_pool_manager import ModelPoolManager
from models.ai_config import AIProviderName
from utils.logger import logger


class ResponseManager:
    """Manages bot responses based on violation levels."""

    def __init__(self, bot: Bot, chat_manager: ChatManager, model_pool_manager: Optional[ModelPoolManager] = None):
        self.bot = bot
        self.chat_manager = chat_manager
        self.model_pool_manager = model_pool_manager

    async def handle_topic_violation(
        self, message: Message, suggested_topic: str, current_topic_name: str
    ) -> None:
        """Handle a topic violation with appropriate response.

        Args:
            message: The message that violated topic rules
            suggested_topic: Name of the suggested appropriate topic
            current_topic_id: ID of the current topic where violation occurred
        """
        # Get violation count for this topic (already recorded in chat_manager)
        violation_count = self.chat_manager.get_violation_count(current_topic_name)

        # Determine response type based on violation count
        response_type = settings.reaction_levels.get(violation_count, "reaction_only")

        logger.info(
            f"Topic violation #{violation_count} detected. Response type: {response_type}"
        )
        if suggested_topic == current_topic_name:
            return
        try:
            if response_type == "reaction_only":
                await self._add_topic_reaction(message, suggested_topic)
            elif response_type == "polite_warning":
                await self._send_polite_warning(message, suggested_topic)
            elif response_type == "angry_warning":
                await self._send_angry_warning(message)

        except Exception as e:
            logger.error(f"Failed to respond to topic violation: {e}")

    async def _add_reaction(self, message: Message) -> None:
        """Add reaction emoji to the message.

        Args:
            message: Message to react to
        """
        try:
            await self.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[{"type": "emoji", "emoji": settings.REACTION_EMOJI}],  # type: ignore
            )
        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")

    async def _add_topic_reaction(self, message: Message, suggested_topic: str) -> None:
        """Add reaction with custom emoji from suggested topic.

        Args:
            message: Message to react to
            suggested_topic: Name of the suggested topic
        """
        try:
            # Get custom emoji ID from suggested topic
            topic_info = self.chat_manager.existing_topics.get(suggested_topic)
            if not topic_info or not topic_info.custom_emoji_id:
                # Fallback to default reaction if no custom emoji
                await self._add_reaction(message)
                return
            
            await self.bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[{"type": "custom_emoji", "custom_emoji_id": topic_info.custom_emoji_id}],  # type: ignore
            )
            logger.info(f"Added custom emoji reaction from topic '{suggested_topic}'")
        except Exception as e:
            logger.error(f"Failed to add topic reaction: {e}")
            # Fallback to default reaction
            await self._add_reaction(message)

    async def _send_polite_warning(
        self, message: Message, suggested_topic: str
    ) -> None:
        """Send a polite warning about topic compliance.

        Args:
            message: Original message that violated rules
            suggested_topic: Suggested appropriate topic
        """
        try:
            warning_text = (
                f"🤔 Кажется, это сообщение больше подходит для темы "
                f"'{suggested_topic}'. Возможно, стоит перенести беседу туда?"
            )

            await message.reply(warning_text)
            logger.info("Sent polite warning for topic violation")

        except TelegramBadRequest as e:
            logger.error(f"Failed to send polite warning: {e}")

    async def _send_angry_warning(self, message: Message) -> None:
        """Send an angry warning about repeated violations.

        Args:
            message: Original message that violated rules
        """
        try:
            angry_text = "🔥 ПРЕКРАТИТЬ ХУЙНЮ! 🔥"

            await message.reply(angry_text)
            logger.info("Sent angry warning for repeated violations")

        except TelegramBadRequest as e:
            logger.error(f"Failed to send angry warning: {e}")
    
    async def generate_ai_response(
        self, 
        message: str, 
        chat_id: int, 
        topic_id: Optional[int] = None,
        allowed_models: Optional[List[str]] = None,
        allowed_providers: Optional[List[AIProviderName]] = None
    ) -> str:
        """Generate AI response using model pool or chat manager.
        
        Args:
            message: The message to respond to
            chat_id: The chat ID
            topic_id: Optional topic ID
            allowed_models: List of allowed model names
            allowed_providers: List of allowed providers
            
        Returns:
            Generated response text
        """
        if self.model_pool_manager:
            # Use model pool to get random client
            ai_client = self.model_pool_manager.get_random_client(
                allowed_models=allowed_models,
                allowed_providers=allowed_providers
            )
            return await ai_client.generate_free_response(message, chat_id, topic_id)
        else:
            # Fall back to chat manager's AI client
            return await self.chat_manager.ai_manager.generate_free_response(message, chat_id, topic_id)
