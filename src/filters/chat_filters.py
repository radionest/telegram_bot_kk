"""Chat-related custom filters."""


from aiogram.types import Message

from services.chat_manager import ChatManager


def is_target_group(msg: Message, chat_manager: ChatManager) -> bool:
    """Check if message is from target group.
    
    This function uses the global configured_chat_filter to maintain
    backward compatibility while using the new centralized group management.
    
    Args:
        msg: Telegram message object
        chat_manager: ChatManager instance (for compatibility)
        
    Returns:
        True if message is from target group, False otherwise
    """
    return msg.chat.id == chat_manager.target_group_chat_id