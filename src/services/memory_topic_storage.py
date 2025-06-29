from typing import Optional, Dict, List, Set, Tuple
from datetime import datetime
from loguru import logger

from models.base_topic_storage import BaseTopicStorage, TopicInfo, GroupTopicsInfo


class MemoryTopicStorage(BaseTopicStorage):
    """In-memory implementation of topic storage.

    Stores topic information in memory using nested dictionaries.
    Structure: {group_id: {topic_id: TopicInfo}}
    """

    def __init__(self):
        """Initialize memory topic storage.

        Creates an empty storage dictionary where:
        - Outer key is group_id
        - Inner key is topic_id (None for general topic)
        - Value is TopicInfo object
        """
        self._storage: Dict[int, Dict[Optional[int], TopicInfo]] = {}

    async def add_topic(self, topic_info: TopicInfo) -> bool:
        """Добавляет новый топик."""
        group_id = topic_info.group_id
        topic_id = topic_info.topic_id

        if group_id not in self._storage:
            self._storage[group_id] = {}

        if topic_id in self._storage[group_id]:
            logger.debug(f"Топик {topic_id} в группе {group_id} уже существует")
            return False

        self._storage[group_id][topic_id] = topic_info
        logger.debug(f"Добавлен топик {topic_id} в группу {group_id}")
        return True

    async def get_topic(
        self, group_id: int, topic_id: Optional[int] = None
    ) -> Optional[TopicInfo]:
        """Получает информацию о топике."""
        if group_id not in self._storage:
            return None

        return self._storage[group_id].get(topic_id)

    async def get_general_topic(self, group_id: int) -> Optional[TopicInfo]:
        """Получает информацию о general topic группы."""
        return await self.get_topic(group_id, None)

    async def get_group_topics(
        self, group_id: int, include_general: bool = True
    ) -> List[TopicInfo]:
        """Получает все топики группы."""
        if group_id not in self._storage:
            return []

        topics = list(self._storage[group_id].values())

        if not include_general:
            topics = [t for t in topics if not t.is_general]

        return topics

    async def update_topic(
        self, group_id: int, topic_id: Optional[int], **kwargs
    ) -> bool:
        """Обновляет информацию о топике."""
        topic = await self.get_topic(group_id, topic_id)
        if not topic:
            logger.debug(f"Топик {topic_id} в группе {group_id} не найден")
            return False

        # Обновляем только разрешенные поля
        allowed_fields = {
            "name",
            "icon_color",
            "icon_emoji_id",
            "is_closed",
            "is_hidden",
            "metadata",
        }

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(topic, field):
                setattr(topic, field, value)

        logger.debug(f"Обновлен топик {topic_id} в группе {group_id}")
        return True

    async def remove_topic(self, group_id: int, topic_id: Optional[int]) -> bool:
        """Удаляет топик."""
        if group_id not in self._storage:
            return False

        if topic_id not in self._storage[group_id]:
            return False

        del self._storage[group_id][topic_id]

        # Удаляем группу если в ней не осталось топиков
        if not self._storage[group_id]:
            del self._storage[group_id]

        logger.debug(f"Удален топик {topic_id} из группы {group_id}")
        return True

    async def remove_group_topics(self, group_id: int) -> int:
        """Удаляет все топики группы."""
        if group_id not in self._storage:
            return 0

        count = len(self._storage[group_id])
        del self._storage[group_id]

        logger.debug(f"Удалено {count} топиков из группы {group_id}")
        return count

    async def topic_exists(self, group_id: int, topic_id: Optional[int]) -> bool:
        """Проверяет существование топика."""
        if group_id not in self._storage:
            return False

        return topic_id in self._storage[group_id]

    async def get_all_groups_with_topics(self) -> List[GroupTopicsInfo]:
        """Получает информацию о всех группах с их топиками."""
        result = []

        for group_id, topics in self._storage.items():
            topics_list = list(topics.values())
            has_general = any(t.is_general for t in topics_list)

            # Получаем название группы из первого топика
            group_title = f"Group {group_id}"
            if topics_list:
                # Можно сохранять название группы в metadata топиков
                first_topic = topics_list[0]
                if first_topic.metadata and "group_title" in first_topic.metadata:
                    group_title = first_topic.metadata["group_title"]

            group_info = GroupTopicsInfo(
                group_id=group_id,
                group_title=group_title,
                topics=topics_list,
                has_general_topic=has_general,
                last_updated=datetime.now(),
            )
            result.append(group_info)

        return result

    async def get_groups_ids(self) -> Set[int]:
        """Получает ID всех групп, имеющих топики."""
        return set(self._storage.keys())

    async def get_topics_count(
        self, group_id: Optional[int] = None, include_general: bool = True
    ) -> int:
        """Получает количество топиков."""
        if group_id is not None:
            if group_id not in self._storage:
                return 0

            topics = list(self._storage[group_id].values())
            if not include_general:
                topics = [t for t in topics if not t.is_general]

            return len(topics)

        # Общее количество топиков
        total = 0
        for group_topics in self._storage.values():
            if include_general:
                total += len(group_topics)
            else:
                total += sum(1 for t in group_topics.values() if not t.is_general)

        return total

    async def search_topics(
        self, query: str, group_id: Optional[int] = None
    ) -> List[TopicInfo]:
        """Поиск топиков по названию."""
        query_lower = query.lower()
        result = []

        if group_id is not None:
            # Поиск в конкретной группе
            if group_id in self._storage:
                for topic in self._storage[group_id].values():
                    if query_lower in topic.name.lower():
                        result.append(topic)
        else:
            # Поиск по всем группам
            for topics in self._storage.values():
                for topic in topics.values():
                    if query_lower in topic.name.lower():
                        result.append(topic)

        return result

    async def has_general_topic(self, group_id: int) -> bool:
        """Проверяет наличие general topic в группе."""
        return await self.topic_exists(group_id, None)

    async def clear_all(self) -> int:
        """Удаляет все данные о топиках."""
        total = await self.get_topics_count()
        self._storage.clear()

        logger.info(f"Очищено хранилище топиков, удалено {total} записей")
        return total

    def _get_topic_key(
        self, group_id: int, topic_id: Optional[int]
    ) -> Tuple[int, Optional[int]]:
        """Helper method to get topic key.

        Args:
            group_id: The group ID
            topic_id: The topic ID (None for general topic)

        Returns:
            Tuple of (group_id, topic_id) used as key
        """
        return (group_id, topic_id)
