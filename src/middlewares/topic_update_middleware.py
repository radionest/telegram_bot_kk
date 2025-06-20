"""Middleware для обновления данных о топиках из входящих сообщений."""

from typing import Callable, Dict, Any, Awaitable, Optional
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger

from models.base_topic_storage import TopicInfo
from services.memory_topic_storage import MemoryTopicStorage


class TopicUpdateMiddleware(BaseMiddleware):
    """Middleware для автоматического обновления информации о топиках из сообщений."""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Обрабатывает входящее сообщение и обновляет данные о топиках."""
        
        # Получаем topic_storage из данных диспетчера
        topic_storage: Optional[MemoryTopicStorage] = data.get("topic_storage")
        if not topic_storage:
            logger.warning("TopicStorage не найден в данных диспетчера")
            return await handler(event, data)
        
        # Обрабатываем только сообщения из групп/супергрупп с форумами
        if event.chat.type not in ["group", "supergroup"]:
            return await handler(event, data)
        
        # Проверяем, что это форум
        if not getattr(event.chat, "is_forum", False):
            return await handler(event, data)
        
        try:
            await self._update_topic_info(event, topic_storage)
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных топика: {e}")
        
        # Продолжаем обработку
        return await handler(event, data)
    
    async def _update_topic_info(self, message: Message, storage: MemoryTopicStorage) -> None:
        """Обновляет информацию о топике из сообщения."""
        
        group_id = message.chat.id
        group_title = message.chat.title or f"Group {group_id}"
        
        # Определяем topic_id
        topic_id = getattr(message, "message_thread_id", None)
        is_topic_message = getattr(message, "is_topic_message", False)
        
        # Если это не сообщение в топике и нет thread_id, то это general topic
        if not is_topic_message and topic_id is None:
            # Это сообщение в general topic
            await self._update_general_topic(group_id, group_title, storage)
        elif topic_id is not None:
            # Это сообщение в конкретном топике
            await self._update_specific_topic(group_id, group_title, topic_id, message, storage)
    
    async def _update_general_topic(
        self, 
        group_id: int, 
        group_title: str, 
        storage: MemoryTopicStorage
    ) -> None:
        """Обновляет информацию о general topic."""
        
        # Проверяем, существует ли уже general topic
        if not await storage.topic_exists(group_id, None):
            # Создаем новый general topic
            topic_info = TopicInfo(
                group_id=group_id,
                topic_id=None,
                name="General",
                is_general=True,
                created_at=datetime.now(),
                metadata={"group_title": group_title}
            )
            
            if await storage.add_topic(topic_info):
                logger.debug(f"Добавлен general topic для группы {group_id} ({group_title})")
        else:
            # Обновляем metadata с названием группы
            await storage.update_topic(
                group_id, 
                None, 
                metadata={"group_title": group_title, "last_seen": datetime.now()}
            )
    
    async def _update_specific_topic(
        self,
        group_id: int,
        group_title: str,
        topic_id: int,
        message: Message,
        storage: MemoryTopicStorage
    ) -> None:
        """Обновляет информацию о конкретном топике."""
        
        # Проверяем, существует ли топик
        if not await storage.topic_exists(group_id, topic_id):
            # Пытаемся получить информацию о топике из reply_to_message
            icon_color = None
            icon_emoji_id = None
            
            # Если это ответ на сообщение создания топика
            if message.reply_to_message and message.reply_to_message.forum_topic_created:
                forum_topic = message.reply_to_message.forum_topic_created
                topic_name = forum_topic.name
                icon_color = getattr(forum_topic, "icon_color", None)
                icon_emoji_id = getattr(forum_topic, "icon_custom_emoji_id", None)
            # Или если это сообщение о редактировании топика
            elif message.forum_topic_edited:
                forum_topic = message.forum_topic_edited
                topic_name = getattr(forum_topic, "name", None)
                icon_emoji_id = getattr(forum_topic, "icon_custom_emoji_id", icon_emoji_id)
            else:
                return
            # Создаем новый топик
            topic_info = TopicInfo(
                group_id=group_id,
                topic_id=topic_id,
                name=topic_name,
                icon_color=icon_color,
                icon_emoji_id=icon_emoji_id,
                is_general=False,
                created_at=datetime.now(),
                metadata={
                    "group_title": group_title,
                    "first_seen_message_id": message.message_id
                }
            )
            
            if await storage.add_topic(topic_info):
                logger.debug(f"Добавлен топик {topic_id} ({topic_name}) в группе {group_id}")
        else:
            # Обновляем metadata
            updates = {
                "metadata": {
                    "group_title": group_title,
                    "last_seen": datetime.now(),
                    "last_message_id": message.message_id
                }
            }
            
            # Обновляем информацию о топике если есть forum_topic_edited
            if message.forum_topic_edited:
                forum_topic = message.forum_topic_edited
                if hasattr(forum_topic, "name") and forum_topic.name:
                    updates["name"] = forum_topic.name
                if hasattr(forum_topic, "icon_custom_emoji_id"):
                    updates["icon_emoji_id"] = forum_topic.icon_custom_emoji_id
                if hasattr(forum_topic, "is_closed"):
                    updates["is_closed"] = forum_topic.is_closed
            
            # Обновляем информацию о закрытии/скрытии топика
            if message.forum_topic_closed:
                updates["is_closed"] = True
            elif message.forum_topic_reopened:
                updates["is_closed"] = False
            
            await storage.update_topic(group_id, topic_id, **updates)