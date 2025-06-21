"""Message handlers for the Telegram bot."""

from aiogram import F, Router, Bot
from aiogram.filters import invert_f
from aiogram.types import Message

from filters.chat_filters import is_target_group
from filters.base import should_analyze_message, is_bot_mentioned, should_bot_random_reply
from services.chat_manager import ChatManager
from services.response_manager import ResponseManager
from services.group_tracker import GroupTracker
from utils.group_selection import send_group_selection_message
from config.settings import settings
from utils.logger import logger

router = Router()
router.message.filter(F.chat.type.in_(["group", "supergroup"]))


@router.message(is_target_group, should_bot_random_reply)
@router.message(is_target_group, is_bot_mentioned)
async def handle_bot_mention(
    message: Message, chat_manager: ChatManager, bot: Bot
) -> None:
    """Handle messages where bot is mentioned.

    Args:
        message: Telegram message object
        chat_manager: Chat manager instance
        bot: Bot instance
    """
    if not message.text:
        return

    username = message.from_user.username or "unknown"  # type: ignore
    logger.info(f"Bot mentioned by {username}: {message.text[:50]}...")

    try:
        # Get topic ID from message if in a forum
        topic_id = None
        if hasattr(message, 'message_thread_id') and message.message_thread_id:
            topic_id = message.message_thread_id
            
        # Generate free-form response
        response = await chat_manager.ai_manager.generate_free_response(
            message=message.text,
            chat_id=message.chat.id,
            topic_id=topic_id
        )

        # Send response as reply
        await message.reply(response)
        logger.info(f"Sent free-form response to {username}")

    except Exception as e:
        logger.error(f"Error handling bot mention: {e}")
        await message.reply("Извините, произошла ошибка при обработке вашего сообщения.")

@router.message(should_analyze_message, is_target_group)
async def handle_group_message(
    message: Message, chat_manager: ChatManager, response_manager: ResponseManager
) -> None:
    """Handle all text messages in groups.

    Args:
        message: Telegram message object
        chat_manager: Chat manager instance
        response_manager: Response manager instance
    """
    username = message.from_user.username or "unknown"  # type: ignore
    logger.debug(
        f"Analyzing topic compliance for message from {username}: {message.text[:50]}..."  # type: ignore
    )

    # Get topic ID from message
    topic = await chat_manager.get_topic_from_message(message)
    if not topic:
        logger.debug("Message not in a forum topic, skipping analysis")
        return

    # Analyze message for topic compliance
    result = await chat_manager.analyze_message_topic(message, topic.name)

    if not result:
        logger.warning("Failed to analyze message topic")
        return

    # If message is not appropriate for current topic
    if not result.is_appropriate and result.suggested_topic:
        await response_manager.handle_topic_violation(
            message=message,
            suggested_topic=result.suggested_topic,
            current_topic_name=topic.name,
        )
    else:
        logger.debug("Message is appropriate for current topic")


@router.message(invert_f(is_target_group))
async def track_group_membership(
    message: Message, bot: Bot, group_tracker: GroupTracker, chat_manager: ChatManager
) -> None:
    """Track bot membership in groups and notify superuser about new groups.

    Args:
        message: Telegram message object
        bot: Bot instance
        group_tracker: Group tracker instance
    """
    if not message.chat or message.chat.type not in ["group", "supergroup"]:
        return

    # Track this group
    is_new_group = group_tracker.add_group(
        group_id=message.chat.id,
        title=message.chat.title or "Unknown",
        username=message.chat.username,
    )
    if is_new_group and len(group_tracker.groups) == 1:
        await chat_manager.set_target_group_chat_id(message.chat.id)
        return

    # If this is a new group and we don't have a target group set, notify superuser
    if is_new_group and not chat_manager.target_group_chat_id:
        try:
            # Send group selection message to superuser
            await send_group_selection_message(
                bot=bot,
                chat_id=settings.SUPERUSER_ID,
                group_tracker=group_tracker,
                chat_manager=chat_manager,
                notification_mode=True,
            )
            logger.info(f"Notified superuser about new group: {message.chat.title}")
        except Exception as e:
            logger.error(f"Failed to notify superuser about new group: {e}")
