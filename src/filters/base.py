"""Base custom filters."""
import random

from aiogram import Bot
from aiogram.types import Message

from config.settings import settings


def is_superadmin(msg: Message):
    """Check if the message sender is the superadmin.
    
    Args:
        msg: The message to check
        
    Returns:
        True if the sender is the superadmin, False otherwise
    """
    return msg.from_user.id == settings.SUPERUSER_ID  # type: ignore


def should_analyze_message(message: Message) -> bool:
    """Determine if message should be analyzed for topic compliance.

    Args:
        message: Message to check

    Returns:
        True if message should be analyzed
    """
    # Don't analyze bot's own messages
    if message.from_user and message.from_user.is_bot:
        return False

    # Don't analyze system messages
    if not message.text:
        return False

    # Don't analyze very short messages (likely reactions/acknowledgments)
    if len(message.text.strip()) < settings.MIN_MESSAGE_LENGTH:
        return False

    # Don't analyze commands
    if message.text.startswith("/"):
        return False

    return True


async def is_bot_mentioned(message: Message, bot: Bot, chat_manager=None) -> bool:
    """Check if bot is mentioned in the message.
    
    Args:
        message: Message to check
        bot: Bot instance
        chat_manager: Optional ChatManager instance with cached bot info
        
    Returns:
        True if bot is mentioned via @username
    """
    if not message.text:
        return False
        
    # Try to get username from chat_manager first
    if chat_manager and chat_manager.bot_username:
        bot_username = chat_manager.bot_username
    else:
        # Fallback to API call if chat_manager not available
        bot_info = await bot.get_me()
        if not bot_info.username:
            return False
        bot_username = bot_info.username
        
    # Check if bot's username is mentioned in the message
    bot_mention = f"@{bot_username}"
    return bot_mention.lower() in message.text.lower()


async def should_bot_random_reply(message: Message, bot: Bot) -> bool:
    """Check if bot should randomly reply to a message.
    
    Args:
        message: Message to check
        bot: Bot instance
        
    Returns:
        True if message is longer than 20 characters and random check passes (3% chance)
    """
    if not message.text:
        return False
        
    return (len(message.text) > 20) and (random.random() < settings.RANDOM_REPLY_PROBABILITY)


async def is_reply_to_bot(message: Message, bot: Bot, chat_manager=None) -> bool:
    """Check if message is a reply to bot's message.
    
    Args:
        message: Message to check
        bot: Bot instance
        chat_manager: Optional ChatManager instance with cached bot info
        
    Returns:
        True if message is a reply to bot's message
    """
    # Check if message is a reply
    if not message.reply_to_message:
        return False
        
    # Check if the original message is from the bot
    if not message.reply_to_message.from_user:
        return False
        
    # Try to get bot ID from chat_manager first
    if chat_manager and chat_manager.bot_id:
        bot_id = chat_manager.bot_id
    else:
        # Fallback to API call if chat_manager not available
        bot_info = await bot.get_me()
        bot_id = bot_info.id
        
    return message.reply_to_message.from_user.id == bot_id