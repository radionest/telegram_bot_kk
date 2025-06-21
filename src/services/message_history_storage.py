from collections import deque, defaultdict
from typing import List, Optional, Dict
from datetime import datetime, timedelta

from aiogram.types import Message
from loguru import logger

from models.message_history import MessageHistoryStorage


class InMemoryMessageHistoryStorage(MessageHistoryStorage):
    """Реализация хранилища истории сообщений в памяти с фокусом на темы."""
    
    def __init__(self, max_messages_per_topic: int = 1000):
        """Инициализация хранилища.
        
        Args:
            max_messages_per_topic: Максимальное количество сообщений на тему
        """
        self.max_messages_per_topic = max_messages_per_topic
        
        # Хранилище по темам: (chat_id, topic_id) -> deque of messages
        # topic_id = None длsrc.я сообщений основного чата
        self._topic_messages: Dict[tuple, deque] = defaultdict(
            lambda: deque(maxlen=max_messages_per_topic)
        )
        
        # Общее хранилище всех сообщений чата для get_recent_messages
        self._all_messages: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=max_messages_per_topic * 10)  # Больше места для всех сообщений
        )
    
    async def save_message(self, message: Message) -> None:
        """Сохранить сообщение в историю."""
        chat_id = message.chat.id
        
        # Определяем topic_id
        topic_id = None
        if hasattr(message, 'message_thread_id') and message.message_thread_id:
            topic_id = message.message_thread_id
        
        # Сохраняем в хранилище по темам
        self._topic_messages[(chat_id, topic_id)].append(message)
        
        # Сохраняем в общее хранилище
        self._all_messages[chat_id].append(message)
        
        logger.debug(f"Сохранено сообщение {message.message_id} в чате {chat_id}, тема {topic_id}")
    
    async def get_topic_messages(
        self, 
        chat_id: int, 
        topic_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Message]:
        """Получить сообщения темы/топика или основного чата."""
        messages = list(self._topic_messages[(chat_id, topic_id)])
        
        # Возвращаем последние limit сообщений
        return messages[-limit:] if len(messages) > limit else messages
    
    async def get_recent_messages(
        self, 
        chat_id: int,
        limit: int = 50
    ) -> List[Message]:
        """Получить последние сообщения в чате независимо от темы."""
        messages = list(self._all_messages[chat_id])
        
        # Возвращаем последние limit сообщений
        return messages[-limit:] if len(messages) > limit else messages
    
    async def cleanup_old_messages(self, days: int = 30) -> int:
        """Очистить старые сообщения."""
        cutoff_date = datetime.now() - timedelta(days=days)
        total_deleted = 0
        
        # Очищаем сообщения по темам
        for key in list(self._topic_messages.keys()):
            topic_deque = self._topic_messages[key]
            new_deque = deque(maxlen=self.max_messages_per_topic)
            
            for message in topic_deque:
                if message.date >= cutoff_date:
                    new_deque.append(message)
                else:
                    total_deleted += 1
            
            self._topic_messages[key] = new_deque
        
        # Очищаем общее хранилище
        for chat_id in list(self._all_messages.keys()):
            all_deque = self._all_messages[chat_id]
            new_deque = deque(maxlen=self.max_messages_per_topic * 10)
            
            for message in all_deque:
                if message.date >= cutoff_date:
                    new_deque.append(message)
            
            self._all_messages[chat_id] = new_deque
        
        logger.info(f"Удалено {total_deleted} старых сообщений")
        return total_deleted
    
    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics.
        
        Returns:
            Dictionary with statistics:
            - total_messages: Total number of messages
            - total_topics: Total number of topics
            - total_chats: Total number of chats
            - max_messages_per_topic: Maximum messages per topic
        """
        total_topics = len(self._topic_messages)
        total_messages = sum(len(msgs) for msgs in self._topic_messages.values())
        total_chats = len(self._all_messages)
        
        return {
            "total_messages": total_messages,
            "total_topics": total_topics,
            "total_chats": total_chats,
            "max_messages_per_topic": self.max_messages_per_topic
        }