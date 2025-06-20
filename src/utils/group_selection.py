"""Utilities for group selection functionality."""

from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.group_tracker import GroupTracker
from services.chat_manager import ChatManager


async def send_group_selection_message(
    bot: Bot,
    chat_id: int,
    group_tracker: GroupTracker,
    chat_manager: ChatManager,
    current_group_id: Optional[int] = None,
    current_group_title: Optional[str] = None,
    notification_mode: bool = False,
) -> None:
    """Send group selection message with keyboard.

    Args:
        bot: Bot instance
        chat_id: Chat ID to send message to
        group_tracker: Group tracker instance
        current_group_id: Current group ID (if command used in group)
        current_group_title: Current group title (if command used in group)
        notification_mode: True if this is a notification about new group
    """
    # Get all tracked groups
    groups = group_tracker.get_groups()

    # Build keyboard
    keyboard_buttons = []

    # Add buttons for each tracked group
    for group_id, group_info in groups.items():
        button_text = f"📍 {group_info['title']}"
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=button_text, callback_data=f"select_group:{group_id}"
                )
            ]
        )

    # Add current group if provided and not in list
    if current_group_id and current_group_id not in groups:
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=f"➕ {current_group_title or 'Текущая группа'}",
                    callback_data=f"select_group:{current_group_id}",
                )
            ]
        )

    # Add cancel button
    keyboard_buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_group_selection")]
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Build status text
    selected_group_id = chat_manager.target_group_chat_id

    if notification_mode:
        # Special text for notification about new group
        newest_group = list(groups.items())[-1] if groups else None
        status_text = "🆕 **Бот добавлен в новую группу!**\n\n"
        if newest_group:
            status_text += f"Группа: **{newest_group[1]['title']}**\n"
            status_text += f"ID: `{newest_group[0]}`\n\n"
        status_text += "Бот пока не настроен для модерации конкретной группы.\n\n"
        if groups:
            status_text += "Доступные группы:\n"
            for gid, info in groups.items():
                status_text += f"• {info['title']} (ID: {gid})\n"
            status_text += "\nВыберите группу для модерации:"
        else:
            status_text += (
                "Используйте команду /set_group чтобы выбрать группу для модерации."
            )
    else:
        # Regular selection mode
        status_text = "🤖 **Выбор группы для модерации**\n\n"

        if selected_group_id:
            # Try to get group info
            group_info = group_tracker.get_group_info(selected_group_id)  # type: ignore
            if group_info:
                status_text += f"Текущая модерируемая группа: **{group_info['title']}** (ID: `{selected_group_id}`)\n\n"
            else:
                status_text += (
                    f"Текущая модерируемая группа ID: `{selected_group_id}`\n\n"
                )
        else:
            status_text += "Модерация не настроена. Выберите группу для модерации.\n\n"

        if groups:
            status_text += "Выберите группу из списка:"
        else:
            status_text += "Бот пока не добавлен ни в одну группу.\n"
            status_text += "Добавьте бота в группу и отправьте там любое сообщение."

    await bot.send_message(
        chat_id=chat_id, text=status_text, reply_markup=keyboard, parse_mode="Markdown"
    )


def format_group_list(groups: dict) -> str:
    """Format groups dictionary to readable list.

    Args:
        groups: Dictionary of groups

    Returns:
        Formatted string with group list
    """
    if not groups:
        return "Нет доступных групп"

    groups_list = ""
    for group_id, info in groups.items():
        groups_list += f"• {info['title']} (ID: {group_id})\n"

    return groups_list
