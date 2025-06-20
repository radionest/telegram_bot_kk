"""Base custom filters."""

from aiogram.types import Message

from config.settings import settings


def is_superadmin(msg: Message):
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
