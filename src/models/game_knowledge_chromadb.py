"""Data models for War Legends game knowledge system with ChromaDB adaptation."""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json

from pydantic import BaseModel, Field


class KnowledgeType(Enum):
    """Types of game knowledge."""
    
    UNIT = "unit"
    BUILDING = "building"
    STRATEGY = "strategy"
    TIMING = "timing"
    PLAYER = "player"
    META = "meta"
    MECHANICS = "mechanics"
    GENERAL = "general"
    ITEM = "item"
    ITEM_SET = "item_set"
    SPELL = "spell"
    HERO = "hero"
    GLOSSARY = "glossary"
    UPDATE = "update"


class KnowledgeSource(Enum):
    """Source of knowledge."""
    
    STATIC = "static"  # From configuration files
    DYNAMIC = "dynamic"  # Extracted from messages
    VERIFIED = "verified"  # Confirmed by multiple sources
    OUTDATED = "outdated"  # Marked as potentially outdated


# Оригинальные модели остаются без изменений
# Импортируем их из существующего файла для переиспользования
from .game_knowledge import (
    Fractions, ItemRarity, Item, ItemSet, Unit, Hero, 
    Building, Spell, Strategy, PlayerInfo, GameMechanic,
    GameUpdate, GlossaryTerm, GeneralKnowledge, KnowledgeUpdate
)


class ChromaDocument(BaseModel):
    """
    Адаптер для конвертации наших моделей в формат ChromaDB документа.
    ChromaDB требует:
    - documents: список текстов для поиска
    - metadatas: список словарей с метаданными
    - ids: уникальные идентификаторы
    - embeddings (опционально): предварительно вычисленные эмбеддинги
    """
    
    id: str
    document: str  # Текстовое представление для поиска
    metadata: Dict[str, Any]  # Все структурированные данные
    
    @classmethod
    def from_knowledge_entry(cls, entry_id: str, knowledge_type: KnowledgeType, 
                           content: Any, source: KnowledgeSource = KnowledgeSource.STATIC,
                           confidence: float = 1.0, tags: List[str] = None,
                           context_tags: List[str] = None) -> 'ChromaDocument':
        """Создает ChromaDocument из любого типа знаний."""
        
        # Генерируем текстовое представление для поиска
        search_text = cls._generate_search_text(knowledge_type, content)
        
        # Конвертируем content в словарь для хранения в metadata
        content_dict = cls._content_to_dict(content)
        
        # Собираем метаданные
        metadata = {
            "type": knowledge_type.value,
            "source": source.value,
            "confidence": confidence,
            "content": json.dumps(content_dict, ensure_ascii=False),  # JSON для сложных структур
            "tags": tags or [],
            "context_tags": context_tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Добавляем специфичные для типа поля в metadata для фильтрации
        if knowledge_type == KnowledgeType.UNIT:
            metadata["unit_name"] = content.name
            metadata["unit_category"] = content.category
            metadata["unit_tier"] = content.tier
            metadata["unit_fraction"] = content.fraction.value
        elif knowledge_type == KnowledgeType.HERO:
            metadata["hero_name"] = content.name
            metadata["hero_category"] = content.category
            metadata["hero_tier"] = content.tier
            metadata["hero_fraction"] = content.fraction.value
        elif knowledge_type == KnowledgeType.BUILDING:
            metadata["building_name"] = content.name
            metadata["building_category"] = content.category
            metadata["building_fraction"] = content.fraction.value
        elif knowledge_type == KnowledgeType.STRATEGY:
            metadata["strategy_name"] = content.name
            metadata["strategy_category"] = content.category
            metadata["strategy_difficulty"] = content.difficulty
        elif knowledge_type == KnowledgeType.PLAYER:
            metadata["player_name"] = content.main_nickname
            metadata["player_clan"] = content.clan
            metadata["player_rating"] = content.rating
        elif knowledge_type == KnowledgeType.ITEM:
            metadata["item_name"] = content.name
            metadata["item_rarity"] = content.rarity.value
            metadata["item_slot"] = content.slot
        elif knowledge_type == KnowledgeType.SPELL:
            metadata["spell_name"] = content.name
            metadata["spell_fraction"] = content.fraction.value
        
        return cls(
            id=entry_id,
            document=search_text,
            metadata=metadata
        )
    
    @staticmethod
    def _generate_search_text(knowledge_type: KnowledgeType, content: Any) -> str:
        """Генерирует текст для полнотекстового поиска."""
        
        parts = []
        
        if knowledge_type in [KnowledgeType.UNIT, KnowledgeType.HERO]:
            parts.extend([
                f"{content.name} - {content.category} юнит уровня {content.tier}",
                f"Фракция: {content.fraction.value}",
                f"Описание: {content.description}",
                f"Стоимость: {', '.join(f'{k}: {v}' for k, v in content.cost.items())}",
                f"Характеристики: {', '.join(f'{k}: {v}' for k, v in content.stats.items())}",
            ])
            if content.counters:
                parts.append(f"Эффективен против: {', '.join(content.counters)}")
            if content.countered_by:
                parts.append(f"Уязвим против: {', '.join(content.countered_by)}")
            if content.special_abilities:
                parts.append(f"Способности: {', '.join(content.special_abilities)}")
            if hasattr(content, 'active_ability_name'):  # Hero specific
                parts.append(f"Активная способность: {content.active_ability_name} - {content.active_ability_description}")
            if content.aliases:
                parts.append(f"Также известен как: {', '.join(content.aliases)}")
                
        elif knowledge_type == KnowledgeType.BUILDING:
            parts.extend([
                f"{content.name} - {content.category} здание",
                f"Фракция: {content.fraction.value}",
                f"Максимальный уровень: {content.max_level}",
                f"Описание: {content.description}",
                f"Эффекты: {json.dumps(content.effects, ensure_ascii=False)}",
            ])
            if content.prerequisites:
                parts.append(f"Требования: {', '.join(content.prerequisites)}")
            if content.aliases:
                parts.append(f"Также известно как: {', '.join(content.aliases)}")
                
        elif knowledge_type == KnowledgeType.STRATEGY:
            parts.extend([
                f"{content.name} - {content.category} стратегия",
                f"Сложность: {content.difficulty}",
                f"Описание: {content.description}",
                f"Состав армии: {', '.join(f'{k}: {v}' for k, v in content.unit_composition.items())}",
            ])
            if content.building_priorities:
                parts.append(f"Приоритет построек: {', '.join(content.building_priorities)}")
            if content.strong_against:
                parts.append(f"Эффективна против: {', '.join(content.strong_against)}")
            if content.counters:
                parts.append(f"Контрится: {', '.join(content.counters)}")
            if content.tips:
                parts.append(f"Советы: {'; '.join(content.tips)}")
            if content.aliases:
                parts.append(f"Также известна как: {', '.join(content.aliases)}")
                
        elif knowledge_type == KnowledgeType.PLAYER:
            parts.extend([
                f"Игрок {content.main_nickname}",
                f"Клан: {content.clan or 'Без клана'}",
                f"Рейтинг: {content.rating or 'Неизвестен'}",
                f"Ранг: {content.rank or 'Неизвестен'}",
            ])
            if content.aliases:
                alias_parts = []
                for key, value in content.aliases.items():
                    alias_parts.append(f"{key}: {value}")
                parts.append(f"Известен также как: {', '.join(alias_parts)}")
            if content.preferred_strategies:
                parts.append(f"Предпочитаемые стратегии: {', '.join(content.preferred_strategies)}")
            if content.play_style_notes:
                parts.append(f"Стиль игры: {'; '.join(content.play_style_notes)}")
            if content.reputation_notes:
                parts.append(f"Репутация: {'; '.join(content.reputation_notes)}")
                
        elif knowledge_type == KnowledgeType.ITEM:
            parts.extend([
                f"{content.name} - {content.rarity.value} предмет для слота {content.slot}",
                f"Максимальный уровень: {content.max_level}",
            ])
            if content.set_name:
                parts.append(f"Часть сета: {content.set_name}")
            if content.aliases:
                parts.append(f"Также известен как: {', '.join(content.aliases)}")
                
        elif knowledge_type == KnowledgeType.SPELL:
            parts.extend([
                f"{content.name} - заклинание фракции {content.fraction.value}",
                f"Стоимость маны: {content.mana_cost}",
                f"Описание: {content.description}",
                f"Максимальный уровень: {content.max_level}",
            ])
            if content.aliases:
                parts.append(f"Также известно как: {', '.join(content.aliases)}")
                
        elif knowledge_type == KnowledgeType.MECHANICS:
            parts.extend([
                f"{content.name} - {content.category} механика",
                f"Описание: {content.description}",
            ])
            if content.formula:
                parts.append(f"Формула: {content.formula}")
            if content.examples:
                parts.append(f"Примеры: {'; '.join(content.examples)}")
            if content.tips:
                parts.append(f"Советы: {'; '.join(content.tips)}")
                
        elif knowledge_type == KnowledgeType.GENERAL:
            parts.extend([
                content.title,
                content.description,
            ])
            if content.aliases:
                parts.append(f"Также известно как: {', '.join(content.aliases)}")
            if content.details:
                parts.append(f"Детали: {json.dumps(content.details, ensure_ascii=False)}")
                
        elif knowledge_type == KnowledgeType.GLOSSARY:
            parts.extend([
                f"{content.term} - игровой термин",
                f"Значение: {content.meaning}",
                f"Контекст: {content.context}",
            ])
            if content.aliases:
                parts.append(f"Также известно как: {', '.join(content.aliases)}")
            if content.examples:
                parts.append(f"Примеры использования: {'; '.join(content.examples)}")
        
        # Добавляем теги для улучшения поиска
        if hasattr(content, 'tags') and content.tags:
            parts.append(f"Теги: {', '.join(content.tags)}")
        
        return ' '.join(filter(None, parts))
    
    @staticmethod
    def _content_to_dict(content: Any) -> Dict[str, Any]:
        """Конвертирует pydantic модель в словарь для хранения в metadata."""
        if hasattr(content, 'model_dump'):
            # Pydantic v2
            return content.model_dump()
        elif hasattr(content, 'dict'):
            # Pydantic v1
            return content.dict()
        elif hasattr(content, '__dataclass_fields__'):
            # Поддержка старых dataclass если они еще остались
            result = {}
            for field_name, field_def in content.__dataclass_fields__.items():
                value = getattr(content, field_name)
                if isinstance(value, Enum):
                    result[field_name] = value.value
                elif isinstance(value, datetime):
                    result[field_name] = value.isoformat()
                elif isinstance(value, list) and value and hasattr(value[0], '__dataclass_fields__'):
                    result[field_name] = [ChromaDocument._content_to_dict(item) for item in value]
                elif hasattr(value, '__dataclass_fields__'):
                    result[field_name] = ChromaDocument._content_to_dict(value)
                else:
                    result[field_name] = value
            return result
        return content
    
    @staticmethod
    def from_metadata(metadata: Dict[str, Any]) -> Any:
        """Восстанавливает оригинальный объект из metadata."""
        content_json = metadata.get('content', '{}')
        content_dict = json.loads(content_json)
        knowledge_type = KnowledgeType(metadata['type'])
        
        # Здесь нужно будет реализовать обратное преобразование для каждого типа
        # Это зависит от конкретных потребностей приложения
        return content_dict


class ChromaSearchResult(BaseModel):
    """Результат поиска в ChromaDB."""
    
    id: str
    document: str
    metadata: Dict[str, Any]
    distance: float  # Расстояние до запроса (чем меньше, тем релевантнее)
    
    @property
    def relevance_score(self) -> float:
        """Преобразует distance в score от 0 до 1 (1 = максимальная релевантность)."""
        # ChromaDB использует L2 distance, конвертируем в score
        return 1 / (1 + self.distance)
    
    def get_content(self) -> Any:
        """Извлекает оригинальный контент из metadata."""
        return ChromaDocument.from_metadata(self.metadata)