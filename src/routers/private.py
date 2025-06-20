"""Message handlers for the Telegram bot."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from config.settings import settings
from utils.logger import logger

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command("start"))
async def start_command(message: Message) -> None:
    """Handle /start command.

    Args:
        message: Telegram message object
    """
    if not message.from_user:
        return

    logger.info(f"Command /start from user {message.from_user.id}")
    await message.answer(
        "Привет! Я бот для контроля соответствия сообщений темам форума.\n"
        "Я слежу за тем, чтобы беседы велись в подходящих темах."
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Handle /help command.

    Args:
        message: Telegram message object
    """
    if not message.from_user:
        return

    logger.info(f"Command /help from user {message.from_user.id}")
    help_text = (
        "Доступные команды:\n"
        "/start - Приветствие\n"
        "/help - Справка\n"
        "/topics - Список доступных тем\n"
    )

    # Add superuser command if applicable
    if settings.SUPERUSER_ID and message.from_user.id == settings.SUPERUSER_ID:
        help_text += (
            "/set_group - Выбрать группу для модерации (только для администратора)\n"
        )

    help_text += (
        "\nЯ анализирую сообщения в группе и проверяю их соответствие темам.\n"
        "При несоответствии реагирую или отправляю предупреждение."
    )
    await message.answer(help_text)


@router.message(F.text)
async def handle_private_message(message: Message) -> None:
    """Handle private messages.

    Args:
        message: Telegram message object
    """
    if not message.from_user:
        return

    logger.warning(f"Private message attempt from user {message.from_user.id}")
    await message.answer(
        "Я работаю только в группах. Добавьте меня в группу, чтобы я мог анализировать сообщения."
    )
