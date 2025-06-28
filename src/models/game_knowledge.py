"""Data models for War Legends game knowledge system."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

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


class KnowledgeSource(Enum):
    """Source of knowledge."""
    
    STATIC = "static"  # From configuration files
    DYNAMIC = "dynamic"  # Extracted from messages
    VERIFIED = "verified"  # Confirmed by multiple sources
    OUTDATED = "outdated"  # Marked as potentially outdated


class Fractions(Enum):
    
    DARK = "dark"  # Тьма
    LIGHT = "light"  # Свет


class ItemRarity(Enum):
    COMMON = "common" # серая
    RARE = "rare" # синька
    EPIC = "epic" # фиолетка


class Item(BaseModel):
    """An equippable item for a unit or hero."""
    name: str
    rarity: ItemRarity
    slot: str  # weapon, armor, helmet, accessory, etc.
    stats_at_level: Dict[int, Dict[str, Any]] = Field(default_factory=dict)  # level -> {"attack": 5, "crit_chance": 0.01}
    max_level: int
    set_name: Optional[str] = None # Принадлежность к сету
    upgrade_cost: Dict[int, int] = Field(default_factory=dict) # level -> gold_cost
    tags: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    
    def get_stats(self, level: int = 1) -> Dict[str, Any]:
        """Get item stats at specific level."""
        level = max(1, min(level, self.max_level))
        return self.stats_at_level.get(level, {})
    
    def get_upgrade_cost_to_level(self, target_level: int) -> int:
        """Get gold cost to upgrade to target level."""
        return self.upgrade_cost.get(target_level, 0)


class ItemSet(BaseModel):
    """Bonus effects for equipping multiple items from the same set."""
    name: str
    item_names: List[str]
    set_bonuses: Dict[int, Dict[str, Any]] # {2: {"health": 50}, 4: {"special_ability": "cleave"}}
    description: str = ""


class Unit(BaseModel):
    """Game unit information with level support."""
    fraction: Fractions    
    name: str
    category: str  # infantry, cavalry, ranged, siege, etc.
    tier: int
    
    # Level-based stats
    stats_at_level: Dict[int, Dict[str, float]] = Field(default_factory=dict)  # level -> {"attack": 100, "defense": 50}
    max_level: int = 1
    
    # Costs and training
    cost_at_level: Dict[int, Dict[str, int]] = Field(default_factory=dict)  # level -> resource costs
    upgrade_cost: Dict[int, int] = Field(default_factory=dict)  # level -> gold cost to upgrade
    build_time: int = 0  # in seconds
    
    # Combat relationships
    counters: List[str] = Field(default_factory=list)  # units it's strong against
    countered_by: List[str] = Field(default_factory=list)  # units it's weak against
    special_abilities_at_level: Dict[int, List[str]] = Field(default_factory=dict)  # level -> abilities
    
    # Equipment and customization
    equipment_slots: List[str] = Field(default_factory=list) # e.g., ["weapon", "armor", "accessory"]
    default_set: Optional[str] = None # Название сета, если он встроенный
    
    # Metadata
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    
    def get_stats(self, level: int = 1) -> Dict[str, float]:
        """Get unit stats at specific level."""
        level = max(1, min(level, self.max_level))
        return self.stats_at_level.get(level, {})
    
    def get_training_cost(self, level: int = 1) -> Dict[str, int]:
        """Get cost to train unit at specific level."""
        level = max(1, min(level, self.max_level))
        return self.cost_at_level.get(level, {})
    
    def get_upgrade_cost_to_level(self, target_level: int) -> int:
        """Get gold cost to upgrade to target level."""
        return self.upgrade_cost.get(target_level, 0)
    
    def get_abilities(self, level: int = 1) -> List[str]:
        """Get all abilities available at specific level."""
        abilities = []
        for lvl in range(1, min(level + 1, self.max_level + 1)):
            if lvl in self.special_abilities_at_level:
                abilities.extend(self.special_abilities_at_level[lvl])
        return abilities


class Hero(Unit):
    """Hero unit with enhanced abilities."""
    # Hero-specific abilities
    active_ability_name: str
    active_ability_description: str
    ability_stats_at_level: Dict[int, Dict[str, float]] = Field(default_factory=dict)  # level -> {"cooldown": 30, "damage": 500}
    passive_bonuses_at_level: Dict[int, List[str]] = Field(default_factory=dict)  # level -> passive bonuses
    
    def get_ability_stats(self, level: int = 1) -> Dict[str, float]:
        """Get hero ability stats at specific level."""
        level = max(1, min(level, self.max_level))
        return self.ability_stats_at_level.get(level, {})
    
    def get_passive_bonuses(self, level: int = 1) -> List[str]:
        """Get all passive bonuses available at specific level."""
        bonuses = []
        for lvl in range(1, min(level + 1, self.max_level + 1)):
            if lvl in self.passive_bonuses_at_level:
                bonuses.extend(self.passive_bonuses_at_level[lvl])
        return bonuses
    
    
class Building(BaseModel):
    """Game building information with level support."""
    
    name: str
    fraction: Fractions
    category: str  # economic, military, defensive, etc.
    max_level: int
    
    # Level-based progression
    stats_at_level: Dict[int, Dict[str, float]] = Field(default_factory=dict)  # level -> {"hit_points": 1000, "armor": 5}
    effects_at_level: Dict[int, Dict[str, Any]] = Field(default_factory=dict)  # level -> production bonuses, unlocks
    upgrade_cost: Dict[int, Dict[str, int]] = Field(default_factory=dict)  # level -> resources
    upgrade_time: Dict[int, int] = Field(default_factory=dict)  # level -> seconds
    
    # Base building info
    prerequisites: List[str] = Field(default_factory=list)
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    
    def get_stats(self, level: int = 1) -> Dict[str, float]:
        """Get building stats at specific level."""
        level = max(1, min(level, self.max_level))
        return self.stats_at_level.get(level, {})
    
    def get_effects(self, level: int = 1) -> Dict[str, Any]:
        """Get building effects at specific level."""
        level = max(1, min(level, self.max_level))
        return self.effects_at_level.get(level, {})
    
    def get_upgrade_cost_to_level(self, target_level: int) -> Dict[str, int]:
        """Get cost to upgrade to target level."""
        return self.upgrade_cost.get(target_level, {})
    
    def get_upgrade_time_to_level(self, target_level: int) -> int:
        """Get time to upgrade to target level."""
        return self.upgrade_time.get(target_level, 0)
    
    def get_total_upgrade_cost(self, from_level: int, to_level: int) -> Dict[str, int]:
        """Calculate total cost to upgrade from one level to another."""
        total_cost = {}
        for lvl in range(from_level + 1, min(to_level + 1, self.max_level + 1)):
            if lvl in self.upgrade_cost:
                for resource, amount in self.upgrade_cost[lvl].items():
                    total_cost[resource] = total_cost.get(resource, 0) + amount
        return total_cost


class Spell(BaseModel):
    """A global player spell/ability, often called a scroll."""
    name: str
    fraction: Fractions
    spell_type: str = "offensive"  # offensive, defensive, utility, buff, debuff
    max_level: int
    
    # Level-based progression
    stats_at_level: Dict[int, Dict[str, float]] = Field(default_factory=dict)  # level -> {"damage": 500, "mana_cost": 50, "cooldown": 30}
    effects_at_level: Dict[int, List[str]] = Field(default_factory=dict)  # level -> text descriptions
    upgrade_cost: Dict[int, Dict[str, int]] = Field(default_factory=dict)  # level -> {"gold": 1000, "cards": 5}
    
    # Base requirements
    unlock_requirements: List[str] = Field(default_factory=list)  # e.g., ["mage_tower_level_3"]
    
    # Metadata
    description: str = ""
    aliases: List[str] = Field(default_factory=list)
    
    def get_stats(self, level: int = 1) -> Dict[str, float]:
        """Get spell stats at specific level."""
        level = max(1, min(level, self.max_level))
        return self.stats_at_level.get(level, {})
    
    def get_effects(self, level: int = 1) -> List[str]:
        """Get spell effects at specific level."""
        level = max(1, min(level, self.max_level))
        return self.effects_at_level.get(level, [])
    
    def get_upgrade_cost_to_level(self, target_level: int) -> Dict[str, int]:
        """Get cost to upgrade to target level."""
        return self.upgrade_cost.get(target_level, {})
    
    def get_damage(self, level: int = 1) -> float:
        """Get spell damage at specific level."""
        stats = self.get_stats(level)
        return stats.get("damage", 0.0)
    
    def get_mana_cost(self, level: int = 1) -> float:
        """Get spell mana cost at specific level."""
        stats = self.get_stats(level)
        return stats.get("mana_cost", 0.0)


class Strategy(BaseModel):
    """Game strategy or build order."""
    
    name: str
    category: str  # rush, boom, turtle, hybrid, etc.
    difficulty: str  # beginner, intermediate, advanced
    timing_windows: List[Dict[str, Any]] = Field(default_factory=list)
    unit_composition: Dict[str, int] = Field(default_factory=dict)
    building_priorities: List[str] = Field(default_factory=list)
    counters: List[str] = Field(default_factory=list)
    strong_against: List[str] = Field(default_factory=list)
    description: str = ""
    tips: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    game_modes: List[str] = Field(default_factory=list) # e.g., ["2v2", "3v3", "arena"]
    aliases: List[str] = Field(default_factory=list)


class PlayerInfo(BaseModel):
    """Player information and statistics."""
    
    # Основные идентификаторы
    main_nickname: str  # Основной игровой ник
    aliases: Dict[str, Any] = Field(default_factory=dict) # {"telegram_id": 540236459, "telegram_username": "Олег", "twitch": "VaLeKekW"}
    
    # Социальная информация
    clan: Optional[str] = None
    clan_history: List[Dict[str, Any]] = Field(default_factory=list) # [{"clan": "КК", "status": "member", "joined": "...", "left": "..."}]
    social_status: List[str] = Field(default_factory=list) # e.g., ["leader", "officer", "tester", "streamer"]
    reputation_notes: List[str] = Field(default_factory=list) # "Считается токсичным", "Вышел из клана после ссоры"
    
    # Игровая информация
    rating: Optional[int] = None
    rank: Optional[str] = None
    preferred_factions: List[Fractions] = Field(default_factory=list)
    preferred_strategies: List[str] = Field(default_factory=list)
    play_style_notes: List[str] = Field(default_factory=list) # "Играет через раш", "Хорошо микроконтролит"
    
    # Мета-данные
    last_seen_active: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list) # "нытик", "активный игрок", "твинковод"


class GameMechanic(BaseModel):
    """Game mechanic explanation."""
    
    name: str
    category: str  # combat, economy, progression, etc.
    description: str
    formula: Optional[str] = None  # mathematical formula if applicable
    examples: List[str] = Field(default_factory=list)
    related_mechanics: List[str] = Field(default_factory=list)
    tips: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)


class GameUpdate(BaseModel):
    """Information about a game patch or update."""
    version: str # e.g., "1.25.10"
    release_date: datetime
    title: str
    summary: str
    change_log: List[str] = Field(default_factory=list)
    player_sentiment: Optional[str] = None # "positive", "negative", "mixed"


class GlossaryTerm(BaseModel):
    """An entry for player-created slang and jargon."""
    term: str # e.g., "Перекач"
    aliases: List[str]
    meaning: str # "Игрок со значительно более высоким уровнем прокачки..."
    context: str # "Обычно используется в негативном ключе для описания дисбаланса."
    examples: List[str] = Field(default_factory=list) # ["Почему мне никто вечно не попадается кроме перекачей"]


class GeneralKnowledge(BaseModel):
    """
    Универсальный объект для хранения различных знаний об игре в свободной форме.
    Используется для всего, что не является юнитом, зданием или заклинанием.
    """
    title: str  # Ключевое название, например "Рейтинг 2v2" или "Фризы в лобби"
    description: str  # Основное текстовое описание сути знания

    # Поля для обогащения и контекста
    aliases: List[str] = Field(default_factory=list)  # Другие названия, например, ["22", "двойки"]
    tags: List[str] = Field(default_factory=list)  # Теги для поиска: ["pvp", "рейтинг", "командный"]
    player_sentiment: Optional[str] = None # Отношение игроков: "негативное", "позитивное", "нейтральное"

    # Словарь для хранения любых дополнительных деталей в "свободной форме"
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Ссылки на сообщения, из которых извлечена информация
    example_message_ids: List[str] = Field(default_factory=list)


class KnowledgeEntry(BaseModel):
    """Generic knowledge entry with metadata."""
    
    id: str
    type: KnowledgeType
    source: KnowledgeSource
    content: Any  # Unit, Building, Strategy, etc.
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    references: List[str] = Field(default_factory=list)  # message IDs or sources
    tags: List[str] = Field(default_factory=list)
    context_tags: List[str] = Field(default_factory=list)  # for relevance matching


class KnowledgeUpdate(BaseModel):
    """Update request for dynamic knowledge."""
    
    message_text: str
    message_id: str
    chat_id: int
    username: str
    timestamp: datetime
    topic_tags: List[str] = Field(default_factory=list)
    extracted_entities: Dict[str, List[str]] = Field(default_factory=dict)  # entity type -> names