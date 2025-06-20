from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from aiogram.types import Message


class MessageHistoryStorage(ABC):
    """Абстрактный класс для управления историей сообщений."""
    
    @abstractmethod
    async def save_message(self, message: Message) -> None:
        """Сохранить сообщение в историю.
        
        Args:
            message: Объект сообщения aiogram для сохранения
        """
        pass
    
    @abstractmethod
    async def get_topic_messages(
        self, 
        chat_id: int, 
        topic_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Message]:
        """Получить сообщения темы/топика или основного чата.
        
        Args:
            chat_id: ID чата
            topic_id: ID темы/топика в супергруппе. None для основного чата
            limit: Максимальное количество сообщений
            
        Returns:
            Список последних сообщений в теме
        """
        pass
    
    @abstractmethod
    async def get_recent_messages(
        self, 
        chat_id: int,
        limit: int = 50
    ) -> List[Message]:
        """Получить последние сообщения в чате независимо от темы.
        
        Args:
            chat_id: ID чата
            limit: Максимальное количество сообщений
            
        Returns:
            Список последних сообщений
        """
        pass
    
    @abstractmethod
    async def cleanup_old_messages(self, days: int = 30) -> int:
        """Очистить старые сообщения.
        
        Args:
            days: Удалить сообщения старше указанного количества дней
            
        Returns:
            Количество удаленных сообщений
        """
        pass