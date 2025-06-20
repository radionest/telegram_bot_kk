from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger


class MessageHistoryMiddleware(BaseMiddleware):
    """Middleware для сохранения сообщений из групповых чатов в историю."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка входящего сообщения.
        
        Args:
            handler: Следующий обработчик в цепочке
            event: Событие сообщения
            data: Дополнительные данные
            
        Returns:
            Результат обработки
        """
        # Получаем storage из dispatcher data
        storage = data.get("message_history_storage")
        
        # Сохраняем только сообщения из групп и супергрупп
        if storage and event.chat.type in ["group", "supergroup"]:
            try:
                await storage.save_message(event)
                logger.debug(
                    f"Сообщение {event.message_id} из чата {event.chat.id} "
                    f"сохранено в историю"
                )
            except Exception as e:
                logger.error(f"Ошибка при сохранении сообщения в историю: {e}")
        
        # Передаем управление следующему обработчику
        return await handler(event, data)