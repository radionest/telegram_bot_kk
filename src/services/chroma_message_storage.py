from typing import List, Optional, Dict
from datetime import datetime, timedelta
from aiogram.types import Message
from loguru import logger

from models.message_history import MessageHistoryStorage
from models.message import StoredMessage
from services.chroma_crud import ChromaCRUD
from exceptions import (
    ChromaDocumentError,
    ChromaSearchError,
    ChromaValidationError,
)


class ChromaMessageHistoryStorage(MessageHistoryStorage):
    """Реализация хранилища истории сообщений с использованием ChromaDB."""

    def __init__(self, chroma_crud: ChromaCRUD, collection_name: str = "telegram_messages"):
        """Инициализация хранилища.

        Args:
            chroma_crud: Экземпляр ChromaCRUD для работы с БД
            collection_name: Название коллекции для хранения сообщений
        """
        self.chroma_crud = chroma_crud
        self.collection_name = collection_name
        self._message_cache: Dict[str, Message] = {}  # Кеш для быстрого доступа

    async def save_message(self, message: Message) -> None:
        """Сохранить сообщение в историю."""
        try:
            # Преобразуем aiogram Message в StoredMessage
            stored_message = StoredMessage.from_aiogram_message(message)

            # Сохраняем в ChromaDB
            await self.chroma_crud.add(stored_message, self.collection_name)

            # Кешируем для быстрого доступа
            cache_key = f"{message.chat.id}_{message.message_id}"
            self._message_cache[cache_key] = message

            # Ограничиваем размер кеша
            if len(self._message_cache) > 1000:
                # Удаляем старые записи
                oldest_keys = list(self._message_cache.keys())[:100]
                for key in oldest_keys:
                    del self._message_cache[key]

            logger.debug(f"Сообщение {message.message_id} сохранено в ChromaDB")

        except ChromaValidationError as e:
            logger.warning(f"Пропуск сообщения из-за валидации: {e}")
        except ChromaDocumentError as e:
            logger.error(f"Ошибка сохранения сообщения в ChromaDB: {e}")

    async def get_topic_messages(
        self, chat_id: int, topic_id: Optional[int] = None, limit: int = 50
    ) -> List[Message]:
        """Получить сообщения темы/топика или основного чата."""
        try:
            # Формируем фильтр для поиска
            where_filter = {"chat_id": chat_id}
            if topic_id is not None:
                where_filter["message_thread_id"] = topic_id

            # Ищем сообщения в ChromaDB
            results = await self.chroma_crud.get_by_metadata(
                {"chat_id": chat_id}, self.collection_name, limit=limit
            )

            # Фильтруем по topic_id если нужно
            if topic_id is not None:
                results = [
                    r
                    for r in results
                    if r["metadata"].get("message_thread_id") == topic_id
                ]

            # Возвращаем закешированные Message объекты если есть
            messages = []
            for result in results[-limit:]:
                cache_key = result["id"]
                if cache_key in self._message_cache:
                    messages.append(self._message_cache[cache_key])

            return messages

        except ChromaSearchError as e:
            logger.error(f"Ошибка получения сообщений темы: {e}")
            return []

    async def get_recent_messages(self, chat_id: int, limit: int = 50) -> List[Message]:
        """Получить последние сообщения в чате независимо от темы."""
        try:
            # Получаем все сообщения чата
            results = await self.chroma_crud.get_by_metadata(
                {"chat_id": chat_id}, self.collection_name, limit=limit
            )

            # Сортируем по timestamp и берем последние
            sorted_results = sorted(
                results,
                key=lambda x: datetime.fromisoformat(x["metadata"]["timestamp"]),
            )

            # Возвращаем закешированные Message объекты если есть
            messages = []
            for result in sorted_results[-limit:]:
                cache_key = result["id"]
                if cache_key in self._message_cache:
                    messages.append(self._message_cache[cache_key])

            return messages

        except ChromaSearchError as e:
            logger.error(f"Ошибка получения последних сообщений: {e}")
            return []

    async def cleanup_old_messages(self, days: int = 30) -> int:
        """Очистить старые сообщения."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            # Получаем информацию о коллекции
            info = await self.chroma_crud.get_collection_info(self.collection_name)
            logger.info(
                f"Начинаем очистку старых сообщений. Всего в БД: {info['count']}"
            )

            # ChromaDB не поддерживает массовое удаление по условию,
            # поэтому логируем предупреждение
            logger.warning(
                "ChromaDB не поддерживает массовое удаление по дате. "
                "Для очистки старых сообщений требуется ручная реализация "
                "или использование отдельного процесса."
            )

            # Очищаем кеш от старых сообщений
            cache_keys_to_delete = []
            for key, message in self._message_cache.items():
                if message.date < cutoff_date:
                    cache_keys_to_delete.append(key)

            for key in cache_keys_to_delete:
                del self._message_cache[key]
                deleted_count += 1

            logger.info(f"Удалено {deleted_count} сообщений из кеша")
            return deleted_count

        except Exception as e:
            logger.error(f"Ошибка при очистке старых сообщений: {e}")
            return 0

    async def search_messages(
        self, query: str, chat_id: Optional[int] = None, limit: int = 10
    ) -> List[Dict]:
        """Семантический поиск сообщений по тексту."""
        try:
            where_filter = {"chat_id": chat_id} if chat_id else None
            results = await self.chroma_crud.search(
                query=query, collection_name=self.collection_name, n_results=limit, where=where_filter
            )
            return results
        except ChromaSearchError as e:
            logger.error(f"Ошибка поиска сообщений: {e}")
            return []

    def get_storage_stats(self) -> Dict[str, int | str]:
        """Get storage statistics."""
        try:
            # Получаем информацию из ChromaDB синхронно через asyncio
            import asyncio

            loop = asyncio.get_event_loop()
            info = loop.run_until_complete(self.chroma_crud.get_collection_info(self.collection_name))

            return {
                "total_messages": info.get("count", 0),
                "cache_size": len(self._message_cache),
                "embedding_model": info.get("embedding_model", "unknown"),
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                "total_messages": 0,
                "cache_size": len(self._message_cache),
                "error": str(e),
            }
