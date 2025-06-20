"""Chat management service for group operations."""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, overload

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from config.settings import settings
from utils.logger import logger
from services.ai_client import AiClient
from services.group_tracker import GroupTracker
from models.analysis import TopicAnalysisRequest, TopicAnalysisResult
from exceptions import ChatManagerError


@dataclass
class TopicInfo:
    """Information about a forum topic."""

    name: str
    description: str
    topic_id: Optional[int] = None
    custom_emoji_id: Optional[str] = None


@dataclass
class ViolationRecord:
    """Record of a topic violation."""

    user_id: int
    topic_name: str
    message_id: int
    suggested_topic: str
    timestamp: datetime


class ChatManager:
    """Manages group chat operations and topic validation."""

    def __init__(
        self,
        bot: Bot,
        ai_manager: AiClient,
        group_tracker: Optional[GroupTracker] = None,
    ):
        self.bot = bot
        self.ai_manager = ai_manager
        self.group_tracker = group_tracker or GroupTracker()
        self.existing_topics: Dict[str, TopicInfo] = {
            t_name: TopicInfo(name=t_name, description=t_description)
            for t_name, t_description in settings.chat_topics.items()
        }
        self.violation_records: Dict[str, deque[ViolationRecord]] = {}
        self.target_group_chat_id: Optional[int] = None

    @property
    def existing_topics_by_id(self) -> Dict[int, TopicInfo]:
        return {topic.topic_id: topic for topic in self.existing_topics.values()}

    async def set_target_group_chat_id(self, group_chat_id: int) -> None:
        """Set the group chat ID for this manager.

        Args:
            group_chat_id: ID of the group chat to manage
        """
        self.target_group_chat_id = group_chat_id
        logger.debug(f"ChatManager group_chat_id updated to: {group_chat_id}")

    async def validate_bot_permissions(self) -> bool:
        """Validate that bot has necessary permissions in the group chat.

        Returns:
            True if bot has all required permissions

        Raises:
            TelegramBadRequest: If chat not found or bot not in chat
            TelegramForbidden: If bot lacks permissions
        """
        if not self.target_group_chat_id:
            logger.warning("Target group not selected.")
            return False

        try:
            chat = await self.bot.get_chat(self.target_group_chat_id)
            chat_member = await self.bot.get_chat_member(
                self.target_group_chat_id, self.bot.id
            )

        except TelegramBadRequest as e:
            logger.error(f"Error validating bot permissions: {e}")
            raise
        except TelegramForbiddenError as e:
            logger.error(f"Bot forbidden from accessing chat: {e}")
            raise

        logger.info(f"Bot status in chat {chat.title}: {chat_member.status}")

        # Check if bot is admin or has necessary permissions
        if chat_member.status not in ["administrator", "creator"]:
            logger.error("Bot is not an administrator in the group chat")
            return False

        # Check specific permissions for forum management
        if (
            hasattr(chat_member, "can_manage_topics")
            and not chat_member.can_manage_topics
        ):
            logger.warning("Bot cannot manage topics - some features may be limited")

        if (
            hasattr(chat_member, "can_post_messages")
            and not chat_member.can_post_messages
        ):
            logger.error("Bot cannot post messages")
            return False

        logger.info("Bot permissions validated successfully")
        return True

    async def check_topic_by_id(self, topic_id: int) -> Optional[TopicInfo]:
        if not self.target_group_chat_id:
            return None

        try:
            # Отправляем тестовое сообщение
            sent_message = await self.bot.send_message(
                chat_id=self.target_group_chat_id,
                text="Тест",
                message_thread_id=topic_id,
            )
        except TelegramBadRequest as e:
            # Топик не существует или закрыт
            if "TOPIC_CLOSED" in str(e):
                logger.debug(f"Topic {topic_id} is closed")
            elif "message thread not found" in str(e).lower():
                logger.debug(f"Topic {topic_id} does not exist")
            return None
        except Exception as e:
            logger.warning(f"Error checking topic {topic_id}: {e}")
            return None

        # Если отправка успешна, топик существует и открыт
        logger.debug(f"Found open topic at ID {topic_id}")

        topic_info = await self.get_topic_from_message(sent_message)

        # Немедленно удаляем тестовое сообщение
        try:
            await self.bot.delete_message(
                chat_id=self.target_group_chat_id, message_id=sent_message.message_id
            )
        except Exception as e:
            logger.warning(f"Failed to delete test message: {e}")

        # Добавляем топик в результаты
        return topic_info

    async def update_existing_topics(self) -> None:
        """Определяет открытые топики в группе путем отправки тестовых сообщений.

        Returns:
            Словарь открытых топиков {topic_id: TopicInfo}
        """
        self.existing_topics = {}
        if not self.target_group_chat_id:
            logger.error("Target group chat ID not set")
            raise ChatManagerError("Target group chat ID not set")

        for potential_id in range(1, 2):
            topic_info = await self.check_topic_by_id(potential_id)
            if topic_info:
                self.add_topic(topic_info=topic_info)

    def record_violation(
        self, user_id: int, topic_name: str, message_id: int, suggested_topic: str
    ) -> None:
        """Record a topic violation.

        Args:
            user_id: ID of the user who violated topic rules
            topic_id: ID of the topic where violation occurred
            message_id: ID of the violating message
            suggested_topic: Name of the suggested appropriate topic
        """
        violation = ViolationRecord(
            user_id=user_id,
            topic_name=topic_name,
            message_id=message_id,
            suggested_topic=suggested_topic,
            timestamp=datetime.now(),
        )

        # Initialize deque if not exists
        if topic_name not in self.violation_records:
            self.violation_records[topic_name] = deque(
                maxlen=settings.VIOLATION_MAX_LENGTH
            )

        self.violation_records[topic_name].append(violation)
        logger.debug(f"Recorded violation for user {user_id} in topic {topic_name}")

    def get_recent_violations(
        self, topic_name: str, time_window_minutes: Optional[int] = None
    ) -> List[ViolationRecord]:
        """Get recent violations for a specific topic.

        Args:
            topic_id: ID of the topic to check
            time_window_minutes: Time window in minutes (default from config)

        Returns:
            List of recent violation records
        """
        if time_window_minutes is None:
            time_window_minutes = settings.VIOLATION_TIME_WINDOW

        # Return empty list if no violations recorded for this topic
        if topic_name not in self.violation_records:
            return []

        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)

        recent_violations = [
            violation
            for violation in self.violation_records[topic_name]
            if violation.timestamp > cutoff_time
        ]

        return recent_violations

    def get_violation_count(self, topic_name: str) -> int:
        """Get count of recent violations for a topic.

        Args:
            topic_id: ID of the topic to check

        Returns:
            Number of recent violations
        """
        return len(self.get_recent_violations(topic_name))

    def reset_violations(self, topic_name: str) -> None:
        """Reset violation counter for a topic.

        Args:
            topic_id: ID of the topic to reset
        """
        # Remove violations for this topic
        # Create new deque without violations for this topic
        self.violation_records[topic_name] = deque(maxlen=settings.VIOLATION_MAX_LENGTH)

        logger.info(f"Reset violation counter for topic {topic_name}")

    @overload
    def add_topic(self, *, topic_id: int, name: str, description: str) -> None: ...

    @overload
    def add_topic(self, *, topic_info: TopicInfo) -> None: ...

    def add_topic(
        self,
        *,
        topic_info: Optional[TopicInfo] = None,
        topic_id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Add a topic to the target topics if it exists in bot config.

        Args:
            topic_id: ID of the topic to add
            name: Name of the topic
            description: Optional description of the topic
        """
        if not topic_info and topic_id and name and description:
            topic_info = TopicInfo(
                topic_id=topic_id, name=name, description=description
            )
        elif topic_info:
            self.existing_topics[topic_info.name] = topic_info
            logger.info(
                f"Added topic {topic_info.name} (ID: {topic_info.topic_id}) to target topics"
            )
        else:
            raise ChatManagerError(
                "You should enter topic_info or topic_id, name,description combination."
            )

    async def get_topic_from_message(self, message: Message) -> Optional[TopicInfo]:
        """Add a topic from message data if it contains topic information.

        Args:
            message: Telegram Message object that may contain topic info

        Returns:
            TopicInfo object if topic was added, None otherwise
        """

        # Check if message has forum topic thread info

        topic_id = getattr(message, "message_thread_id", None)

        match message:
            case Message(forum_topic_created=forum_topic) if forum_topic:
                topic_name = forum_topic.name
                custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
                logger.debug(f"Found topic name from forum_topic_created: {topic_name}")
            case Message(reply_to_message=Message(forum_topic_created=forum_topic)) if (
                forum_topic
            ):
                topic_name = forum_topic.name
                custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
                logger.debug(f"Found topic name from reply: {topic_name}")
            case Message(message_thread_id=topic_tread_id) if topic_tread_id and (
                topic := self.existing_topics_by_id.get(topic_tread_id)
            ):
                topic_name = topic.name
            case Message(message_thread_id=topic_tread_id,
                         is_topic_message=is_topic) if topic_tread_id and is_topic:
                topic = await self.check_topic_by_id(topic_tread_id)
                if topic:
                    self.existing_topics[topic.name].topic_id = topic.topic_id
                    topic_name = topic.name
                else:
                    topic_name = None
            case _:
                logger.debug(
                    f"Topic name not found for message: {message.text} {message.is_topic_message}"
                )
                topic_name = "Основной чат"  # Default name

        if topic_name not in settings.chat_topics:
            logger.debug(
                f"Cant get topic with name {topic_name} because it is absent in config."
            )
            return None
        # Add the topic
        custom_emoji_id = locals().get('custom_emoji_id')
        return TopicInfo(
            topic_id=topic_id,
            name=topic_name,
            description=settings.chat_topics[topic_name],
            custom_emoji_id=custom_emoji_id,
        )

    async def add_topic_from_message(self, message: Message) -> Optional[TopicInfo]:
        """Add a topic from message data if it contains topic information.

        Args:
            message: Telegram Message object that may contain topic info

        Returns:
            TopicInfo object if topic was added, None otherwise
        """

        # Check if message has forum topic thread info
        topic_info = await self.get_topic_from_message(message)
        if not topic_info:
            return None
        self.add_topic(topic_info=topic_info)
        logger.info(
            f"Added topic from message: {topic_info.name} (ID: {topic_info.topic_id})"
        )

        return topic_info

    async def update_topic_custom_emoji(self, message: Message) -> None:
        """Update custom emoji ID for existing topics from message.
        
        Args:
            message: Message that may contain forum topic info with custom emoji
        """
        # Try to extract custom emoji from message
        custom_emoji_id = None
        topic_name = None
        
        match message:
            case Message(forum_topic_created=forum_topic) if forum_topic:
                topic_name = forum_topic.name
                custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
            case Message(reply_to_message=Message(forum_topic_created=forum_topic)) if forum_topic:
                topic_name = forum_topic.name
                custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
                
        # Update existing topic if we found custom emoji
        if topic_name and custom_emoji_id and topic_name in self.existing_topics:
            self.existing_topics[topic_name].custom_emoji_id = custom_emoji_id
            logger.info(f"Updated custom emoji for topic '{topic_name}': {custom_emoji_id}")

    async def test_topic_emoji_detection(self, topic_id: int) -> Optional[str]:
        """Test topic custom emoji detection by sending and analyzing a test message.
        
        Args:
            topic_id: ID of the topic to test
            
        Returns:
            Custom emoji ID if detected, None otherwise
        """
        if not self.target_group_chat_id:
            logger.error("Target group chat ID not set")
            return None
            
        try:
            # Send test message to topic
            test_message = await self.bot.send_message(
                chat_id=self.target_group_chat_id,
                text="🔍 Testing topic info",
                message_thread_id=topic_id,
            )
            
            # Analyze message to extract topic info
            custom_emoji_id = await self._analyze_test_message(test_message)
            
            # Delete test message
            await self._delete_test_message(test_message)
            
            return custom_emoji_id
            
        except Exception as e:
            logger.error(f"Error testing topic {topic_id}: {e}")
            return None
    
    async def _analyze_test_message(self, message: Message) -> Optional[str]:
        """Analyze test message to extract topic information.
        
        Args:
            message: Test message sent to topic
            
        Returns:
            Custom emoji ID if found, None otherwise
        """
        logger.debug(f"Analyzing test message {message.message_id}")
        
        # Log all message attributes for debugging
        logger.debug(f"Message attributes: {message.__dict__}")
        
        # Check various ways topic info might be present
        custom_emoji_id = None
        
        # Check forum_topic_created
        if hasattr(message, 'forum_topic_created') and message.forum_topic_created:
            forum_topic = message.forum_topic_created
            custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
            logger.info(f"Found custom emoji from forum_topic_created: {custom_emoji_id}")
            
        # Check reply_to_message
        elif hasattr(message, 'reply_to_message') and message.reply_to_message:
            reply = message.reply_to_message
            if hasattr(reply, 'forum_topic_created') and reply.forum_topic_created:
                forum_topic = reply.forum_topic_created
                custom_emoji_id = getattr(forum_topic, 'icon_custom_emoji_id', None)
                logger.info(f"Found custom emoji from reply: {custom_emoji_id}")
                
        # Log if no emoji found
        if not custom_emoji_id:
            logger.warning("No custom emoji found in test message")
            
        return custom_emoji_id
    
    async def _delete_test_message(self, message: Message) -> None:
        """Delete test message from chat.
        
        Args:
            message: Message to delete
        """
        try:
            await self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id
            )
            logger.debug(f"Deleted test message {message.message_id}")
        except Exception as e:
            logger.warning(f"Failed to delete test message: {e}")

    async def analyze_message_topic(
        self, message: Message, topic_name: str
    ) -> Optional[TopicAnalysisResult]:
        """Analyze if message is appropriate for current topic.

        Args:
            message: Telegram message to analyze
            topic_id: ID of the current topic

        Returns:
            Analysis result or None if analysis failed
        """
        if not message.from_user or not message.text:
            logger.warning(
                "Message with empty text or unknown user cannot be analized."
            )
            return None

        # Update custom emoji if available
        await self.update_topic_custom_emoji(message)

        # Get current topic info
        topic_info = self.existing_topics.get(topic_name)
        if not topic_info:
            logger.warning(f"Topic {topic_name} not found in target topics")
            topic_info = await self.add_topic_from_message(message)
            if not topic_info:
                return None
        # TODO: REWRITE above

        current_topic = topic_info.name or "Основной чат"

        # Create topic analysis request
        request = TopicAnalysisRequest(
            message_text=message.text,
            current_topic=current_topic,
            current_topic_description=settings.chat_topics.get(current_topic, ""),
            available_topics=self.existing_topics.values(),
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            message_id=message.message_id,
            topic_id=getattr(message, "message_thread_id", None),
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
        )

        # Analyze topic compliance
        try:
            result = await self.ai_manager.analyze_topic_compliance(request)
        except Exception as e:
            logger.error(f"Error analyzing topic compliance: {str(e)}")
            return None

        logger.debug(
            f"Topic analysis result: appropriate={result.is_appropriate}, "
            f"suggested='{result.suggested_topic}', confidence={result.confidence}"
        )

        # Record violation if message is not appropriate
        if not result.is_appropriate \
           and result.suggested_topic \
           and result.suggested_topic != current_topic:
            
            logger.info(
                f"Topic violation detected: '{current_topic}' -> '{result.suggested_topic}'"
            )
            self.record_violation(
                user_id=message.from_user.id,
                topic_name=topic_name,
                message_id=message.message_id,
                suggested_topic=result.suggested_topic,
            )

        return result
