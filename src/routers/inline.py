"""Inline query handlers for the bot."""

import random
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.enums import ParseMode
import hashlib

from services.response_manager import ResponseManager
from utils.logger import logger

router = Router()

# Ответы на пустой запрос
EMPTY_QUERY_RESPONSES = [
    "Что надо?",
    "Чего?",
    "Да?",
    "Слушаю",
    "М?",
    "Ну?",
    "Говори",
    "Че хотел?",
    "А?",
    "Чё там?"
]


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, response_manager: ResponseManager) -> None:
    """Handle inline queries for free-form responses.
    
    Args:
        inline_query: Telegram inline query object
        response_manager: Response manager instance
    """
    query_text = inline_query.query.strip()
    
    try:
        if not query_text:
            # Случайный ответ на пустой запрос
            random_response = random.choice(EMPTY_QUERY_RESPONSES)
            results = [
                InlineQueryResultArticle(
                    id="empty",
                    title=random_response,
                    description="Нажмите чтобы отправить",
                    input_message_content=InputTextMessageContent(
                        message_text=random_response
                    )
                )
            ]
            await inline_query.answer(results, cache_time=1)
            return
        
        logger.info(f"Processing inline query: {query_text[:50]}...")
        
        # Create a unique ID for this query
        query_id = hashlib.md5(query_text.encode()).hexdigest()[:16]
        
        # Get AI response through chat manager's AI client
        ai_response = await response_manager.chat_manager.ai_manager.generate_free_response(query_text)
        
        if ai_response:
            # Просто текст ответа, без форматирования
            results = [
                InlineQueryResultArticle(
                    id=query_id,
                    title="Ответ",
                    description=ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
                    input_message_content=InputTextMessageContent(
                        message_text=ai_response
                    )
                )
            ]
        else:
            results = [
                InlineQueryResultArticle(
                    id="error",
                    title="Не понял",
                    description="Попробуй по-другому",
                    input_message_content=InputTextMessageContent(
                        message_text="Не понял, попробуй по-другому"
                    )
                )
            ]
        
        await inline_query.answer(results, cache_time=10)
        
    except Exception as e:
        logger.error(f"Error processing inline query: {e}")
        error_results = [
            InlineQueryResultArticle(
                id="error",
                title="Ошибка",
                description="Что-то пошло не так",
                input_message_content=InputTextMessageContent(
                    message_text="Ошибка, попробуй позже"
                )
            )
        ]
        await inline_query.answer(error_results, cache_time=10)