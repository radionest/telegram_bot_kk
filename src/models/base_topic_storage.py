from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Set
from datetime import datetime

from pydantic import BaseModel, Field


class TopicInfo(BaseModel):
    """Информация о топике в группе."""
    group_id: int
    topic_id: Optional[int] = None  # None для general topic
    name: str
    icon_color: Optional[int] = None
    icon_emoji_id: Optional[str] = None
    created_at: Optional[datetime] = None
    is_closed: bool = False
    is_hidden: bool = False
    is_general: bool = False  # True для general topic
    metadata: Optional[Dict[str, Any]] = None


class GroupTopicsInfo(BaseModel):
    """Информация о группе и её топиках."""
    group_id: int
    group_title: str
    topics: List[TopicInfo]
    has_general_topic: bool
    last_updated: datetime = Field(default_factory=datetime.now)
    is_forum: bool = True


class BaseTopicStorage(ABC):
    """Абстрактный класс для хранения данных о топиках внутри групп."""
    
    @abstractmethod
    async def add_topic(self, topic_info: TopicInfo) -> bool:
        """Добавляет новый топик.
        
        Args:
            topic_info: Информация о топике
            
        Returns:
            True если топик успешно добавлен, False если уже существует
        """
        pass
    
    @abstractmethod
    async def get_topic(self, group_id: int, topic_id: Optional[int] = None) -> Optional[TopicInfo]:
        """Получает информацию о топике.
        
        Args:
            group_id: ID группы
            topic_id: ID топика (None для general topic)
            
        Returns:
            Информация о топике или None если не найден
        """
        pass
    
    @abstractmethod
    async def get_general_topic(self, group_id: int) -> Optional[TopicInfo]:
        """Получает информацию о general topic группы.
        
        Args:
            group_id: ID группы
            
        Returns:
            Информация о general topic или None если не найден
        """
        pass
    
    @abstractmethod
    async def get_group_topics(self, group_id: int, include_general: bool = True) -> List[TopicInfo]:
        """Получает все топики группы.
        
        Args:
            group_id: ID группы
            include_general: Включать ли general topic в результат
            
        Returns:
            Список топиков группы
        """
        pass
    
    @abstractmethod
    async def update_topic(self, group_id: int, topic_id: Optional[int], **kwargs) -> bool:
        """Обновляет информацию о топике.
        
        Args:
            group_id: ID группы
            topic_id: ID топика (None для general topic)
            **kwargs: Поля для обновления
            
        Returns:
            True если обновление успешно, False если топик не найден
        """
        pass
    
    @abstractmethod
    async def remove_topic(self, group_id: int, topic_id: Optional[int]) -> bool:
        """Удаляет топик.
        
        Args:
            group_id: ID группы
            topic_id: ID топика (None для general topic)
            
        Returns:
            True если удаление успешно, False если топик не найден
        """
        pass
    
    @abstractmethod
    async def remove_group_topics(self, group_id: int) -> int:
        """Удаляет все топики группы.
        
        Args:
            group_id: ID группы
            
        Returns:
            Количество удаленных топиков
        """
        pass
    
    @abstractmethod
    async def topic_exists(self, group_id: int, topic_id: Optional[int]) -> bool:
        """Проверяет существование топика.
        
        Args:
            group_id: ID группы
            topic_id: ID топика (None для general topic)
            
        Returns:
            True если топик существует
        """
        pass
    
    @abstractmethod
    async def get_all_groups_with_topics(self) -> List[GroupTopicsInfo]:
        """Получает информацию о всех группах с их топиками.
        
        Returns:
            Список групп с топиками
        """
        pass
    
    @abstractmethod
    async def get_groups_ids(self) -> Set[int]:
        """Получает ID всех групп, имеющих топики.
        
        Returns:
            Множество ID групп
        """
        pass
    
    @abstractmethod
    async def get_topics_count(self, group_id: Optional[int] = None, include_general: bool = True) -> int:
        """Получает количество топиков.
        
        Args:
            group_id: ID группы (если None - общее количество)
            include_general: Учитывать ли general topics
            
        Returns:
            Количество топиков
        """
        pass
    
    @abstractmethod
    async def search_topics(self, query: str, group_id: Optional[int] = None) -> List[TopicInfo]:
        """Поиск топиков по названию.
        
        Args:
            query: Строка поиска
            group_id: ID группы для поиска (если None - поиск по всем)
            
        Returns:
            Список найденных топиков
        """
        pass
    
    @abstractmethod
    async def has_general_topic(self, group_id: int) -> bool:
        """Проверяет наличие general topic в группе.
        
        Args:
            group_id: ID группы
            
        Returns:
            True если general topic существует
        """
        pass
    
    @abstractmethod
    async def clear_all(self) -> int:
        """Удаляет все данные о топиках.
        
        Returns:
            Количество удаленных топиков
        """
        pass