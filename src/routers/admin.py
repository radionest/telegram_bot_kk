"""Admin command handlers for the Telegram bot."""

from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from filters.base import is_superadmin
from services.group_tracker import GroupTracker
from services.chat_manager import ChatManager
from utils.group_selection import send_group_selection_message
from utils.logger import logger

router = Router()
router.message.filter(is_superadmin)
router.callback_query.filter(is_superadmin)


@router.message(Command("set_group"), F.chat.type == "private")
async def set_group_command(
    message: Message, bot: Bot, chat_manager: ChatManager, group_tracker: GroupTracker
) -> None:
    """Handle /set_group command - select group for moderation.

    Args:
        message: Telegram message object
        bot: Bot instance
        group_tracker: Group tracker instance
    """
    if not message.from_user:
        return

    logger.info(f"Command /set_group from superuser {message.from_user.id}")

    await send_group_selection_message(
        bot=bot,
        chat_id=message.chat.id,
        chat_manager=chat_manager,
        group_tracker=group_tracker,
    )


@router.callback_query(F.data.startswith("select_group:"))
@router.callback_query(F.data == "cancel_group_selection")
async def handle_group_selection(
    callback: CallbackQuery, group_tracker: GroupTracker, chat_manager: ChatManager
) -> None:
    """Handle group selection callback.

    Args:
        callback: Callback query
        group_tracker: Group tracker instance
        chat_manager: Chat manager instance
    """
    if not callback.data:
        await callback.answer()
        return

    if callback.data == "cancel_group_selection":
        if callback.message and hasattr(callback.message, "edit_text"):
            await callback.message.edit_text("Выбор группы отменен.")
        await callback.answer()
        return

    if callback.data.startswith("select_group:"):
        group_id = int(callback.data.split(":")[1])
        await chat_manager.set_target_group_chat_id(group_id)

        try:
            # Get group info from tracker or bot
            group_info = group_tracker.get_group_info(group_id)
            if not group_info:
                # Try to get from bot
                chat_info = await callback.bot.get_chat(group_id)  # type: ignore
                group_title = chat_info.title
                # Add to tracker
                group_tracker.add_group(
                    group_id=group_id,
                    title=group_title or "",
                    username=chat_info.username,
                )
            else:
                group_title = group_info["title"]

            if callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(
                    f"✅ Группа для модерации установлена:\n"
                    f"<b>{group_title}</b>\n\n"
                    f"Теперь бот будет отслеживать сообщения только в этой группе.",
                    parse_mode="HTML",
                )
            logger.info(f"Group {group_id} selected for moderation")
        except Exception as e:
            if callback.message and hasattr(callback.message, "edit_text"):
                await callback.message.edit_text(f"Ошибка при выборе группы: {str(e)}")
            logger.error(f"Error selecting group {group_id}: {e}")

        await callback.answer()


@router.message(Command("topics"))
async def topics_command(message: Message, chat_manager: ChatManager) -> None:
    """Handle /topics command - show available topics.

    Args:
        message: Telegram message object
        chat_manager: Chat manager instance
    """

    logger.info(f"Command /topics from user {message.from_user.id}")  # type: ignore

    topics_text = "📋 Доступные темы форума:\n\n"
    for topic in chat_manager.existing_topics.values():
        topics_text += f"• **{topic.name}**\n  {topic.topic_id}\n\n"

    await message.answer(topics_text, parse_mode="Markdown")
