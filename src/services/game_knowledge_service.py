"""Service for managing War Legends game knowledge with SQLite and JSONB storage."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

from loguru import logger

from models.game_knowledge import (
    KnowledgeEntry,
    KnowledgeType,
    KnowledgeSource,
    KnowledgeUpdate,
    Unit,
    Building,
    Strategy,
    PlayerInfo,
    GameMechanic,
)
from services.knowledge_crud_service import KnowledgeCRUDService


class GameKnowledgeService:
    """Service for managing game knowledge with SQLite storage."""

    def __init__(
        self,
        db_path: Path = Path("src/knowledge/game_knowledge.db"),
        static_knowledge_path: Path = Path("src/knowledge/data"),
        cache_ttl: int = 3600,
    ):
        """Initialize the game knowledge service.

        Args:
            db_path: Path to SQLite database
            static_knowledge_path: Path to static knowledge configuration files
            cache_ttl: Cache time-to-live in seconds
        """
        self.db_path = db_path
        self.static_path = static_knowledge_path
        self.cache_ttl = cache_ttl

        # Initialize CRUD service
        self.crud = KnowledgeCRUDService(db_path)

        # Context cache
        self.context_cache: Dict[str, tuple[str, datetime]] = {}

        # Dynamic knowledge update queue
        self.update_queue: asyncio.Queue = asyncio.Queue()
        self.update_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize database."""
        await self.crud.initialize_database()

    async def add_knowledge_entry(self, entry: KnowledgeEntry):
        """Add a single knowledge entry to database."""
        success = await self.crud.create(entry)
        if success:
            logger.debug(f"Added knowledge entry: {entry.id}")
        else:
            logger.error(f"Failed to add knowledge entry: {entry.id}")

    async def add_knowledge_entries(self, entries: List[KnowledgeEntry]):
        """Add multiple knowledge entries to database."""
        if entries:
            count = await self.crud.create_batch(entries)
            logger.info(f"Added {count} knowledge entries")

    async def create_unit(
        self,
        unit_id: str,
        unit: Unit,
        source: KnowledgeSource = KnowledgeSource.STATIC,
        tags: Optional[List[str]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """Create and store a unit entry."""
        entry = KnowledgeEntry(
            id=f"unit_{unit_id}",
            type=KnowledgeType.UNIT,
            source=source,
            content=unit,
            tags=tags or [],
            context_tags=context_tags or [],
        )
        await self.add_knowledge_entry(entry)
        return entry

    async def create_building(
        self,
        building_id: str,
        building: Building,
        source: KnowledgeSource = KnowledgeSource.STATIC,
        tags: Optional[List[str]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """Create and store a building entry."""
        entry = KnowledgeEntry(
            id=f"building_{building_id}",
            type=KnowledgeType.BUILDING,
            source=source,
            content=building,
            tags=tags or [],
            context_tags=context_tags or [],
        )
        await self.add_knowledge_entry(entry)
        return entry

    async def create_strategy(
        self,
        strategy_id: str,
        strategy: Strategy,
        source: KnowledgeSource = KnowledgeSource.STATIC,
        tags: Optional[List[str]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """Create and store a strategy entry."""
        entry = KnowledgeEntry(
            id=f"strategy_{strategy_id}",
            type=KnowledgeType.STRATEGY,
            source=source,
            content=strategy,
            tags=tags or [],
            context_tags=context_tags or [],
        )
        await self.add_knowledge_entry(entry)
        return entry

    async def create_mechanic(
        self,
        mechanic_id: str,
        mechanic: GameMechanic,
        source: KnowledgeSource = KnowledgeSource.STATIC,
        tags: Optional[List[str]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> KnowledgeEntry:
        """Create and store a game mechanic entry."""
        entry = KnowledgeEntry(
            id=f"mechanic_{mechanic_id}",
            type=KnowledgeType.MECHANICS,
            source=source,
            content=mechanic,
            tags=tags or [],
            context_tags=context_tags or [],
        )
        await self.add_knowledge_entry(entry)
        return entry

    async def get_game_context(
        self,
        topic: str,
        tags: Optional[List[str]] = None,
        message_context: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """Get relevant game context for a topic."""
        # Check cache first
        cache_key = f"{topic}:{','.join(tags or [])}:{limit}"
        if cache_key in self.context_cache:
            context, timestamp = self.context_cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                return context

        # Find relevant knowledge entries
        relevant_entries = await self._find_relevant_entries(
            topic, tags, message_context, limit
        )

        # Format context
        context = self._format_context(relevant_entries)

        # Cache the result
        self.context_cache[cache_key] = (context, datetime.now())

        return context

    async def _find_relevant_entries(
        self,
        topic: str,
        tags: Optional[List[str]] = None,
        message_context: Optional[str] = None,
        limit: int = 5,
    ) -> List[KnowledgeEntry]:
        """Find relevant knowledge entries from database."""
        # Build search query
        search_terms = [topic]
        if tags:
            search_terms.extend(tags)

        # Use FTS for initial search
        fts_query = " OR ".join(search_terms)
        results = await self.crud.search_fts(fts_query, limit=limit * 2)

        # If no FTS results, fall back to tag search
        if not results and tags:
            results = await self.crud.search_by_tags(tags, match_all=False, limit=limit)

        # Score and re-rank results
        scored_results = []
        for entry in results:
            score = self._calculate_relevance_score(entry, topic, tags, message_context)
            scored_results.append((score, entry))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored_results[:limit]]

    def _calculate_relevance_score(
        self,
        entry: KnowledgeEntry,
        topic: str,
        tags: Optional[List[str]],
        message_context: Optional[str],
    ) -> float:
        """Calculate relevance score for a knowledge entry."""
        # message_context reserved for future context-aware scoring
        _ = message_context
        score = 0.0

        # Base confidence score
        score += entry.confidence * 0.3

        # Tag matching
        if tags:
            entry_tags = set(entry.tags + entry.context_tags)
            if hasattr(entry.content, "tags"):
                entry_tags.update(entry.content.tags)
            tag_overlap = len(set(tags) & entry_tags)
            score += tag_overlap * 0.2

        # Topic keyword matching
        topic_words = set(topic.lower().split())
        entry_text = self._get_searchable_text(entry).lower()
        for word in topic_words:
            if word in entry_text:
                score += 0.1

        # Source weight
        source_weights = {
            KnowledgeSource.VERIFIED: 0.3,
            KnowledgeSource.STATIC: 0.2,
            KnowledgeSource.DYNAMIC: 0.1,
            KnowledgeSource.OUTDATED: 0.0,
        }
        score += source_weights.get(entry.source, 0.0)

        return score

    def _get_searchable_text(self, entry: KnowledgeEntry) -> str:
        """Extract searchable text from entry."""
        parts = []

        # Add tags
        parts.extend(entry.tags + entry.context_tags)

        # Add content fields
        content = entry.content
        if hasattr(content, "name"):
            parts.append(content.name)
        if hasattr(content, "description"):
            parts.append(content.description)
        if hasattr(content, "category"):
            parts.append(content.category)
        if hasattr(content, "tags"):
            parts.extend(content.tags)

        return " ".join(parts)

    def _format_context(self, entries: List[KnowledgeEntry]) -> str:
        """Format entries into context string."""
        if not entries:
            return self._get_general_game_info()

        context_parts = ["=== КОНТЕКСТ ИГРЫ WAR LEGENDS ===\n"]

        # Group by type
        from collections import defaultdict

        entries_by_type: Dict[KnowledgeType, List[KnowledgeEntry]] = defaultdict(list)
        for entry in entries:
            entries_by_type[entry.type].append(entry)

        # Format each type section
        type_names = {
            KnowledgeType.UNIT: "ЮНИТЫ",
            KnowledgeType.BUILDING: "ЗДАНИЯ",
            KnowledgeType.STRATEGY: "СТРАТЕГИИ",
            KnowledgeType.MECHANICS: "МЕХАНИКИ",
            KnowledgeType.PLAYER: "ИГРОКИ",
            KnowledgeType.META: "МЕТА",
            KnowledgeType.TIMING: "ТАЙМИНГИ",
            KnowledgeType.GENERAL: "ОБЩЕЕ",
        }

        for knowledge_type, type_entries in entries_by_type.items():
            if type_entries:
                context_parts.append(
                    f"\n{type_names.get(knowledge_type, knowledge_type.value.upper())}:"
                )
                for entry in type_entries:
                    context_parts.append(self._format_entry(entry))

        return "\n".join(context_parts)

    def _format_entry(self, entry: KnowledgeEntry) -> str:
        """Format a single knowledge entry."""
        content = entry.content

        if isinstance(content, Unit):
            return f"""
- {content.name} ({content.category}, Уровень {content.tier})
  Статы: {self._format_dict(content.stats)}
  Сильна против: {', '.join(content.counters) or 'нет данных'}
  Слаба против: {', '.join(content.countered_by) or 'нет данных'}
  {content.description}"""

        elif isinstance(content, Strategy):
            return f"""
- {content.name} ({content.category}, Сложность: {content.difficulty})
  {content.description}
  Состав армии: {self._format_dict(content.unit_composition)}
  Эффективна против: {', '.join(content.strong_against) or 'нет данных'}"""

        elif isinstance(content, GameMechanic):
            return f"""
- {content.name}: {content.description}
  {f'Формула: {content.formula}' if content.formula else ''}"""

        else:
            return f"- {str(content)}"

    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format dictionary for display."""
        if not d:
            return "нет данных"
        return ", ".join(f"{k}: {v}" for k, v in d.items())

    def _get_general_game_info(self) -> str:
        """Get general game information."""
        return """
War Legends - это мобильная RTS игра с следующими основными элементами:
- Различные типы юнитов (пехота, кавалерия, стрелки, осадные орудия)
- Система зданий и улучшений
- Клановые войны и PvP сражения
- Различные стратегии игры (раш, бум, защита)
- Система рейтинга игроков

Для более точной информации укажите конкретную тему или аспект игры."""

    async def update_knowledge_from_message(self, update: KnowledgeUpdate):
        """Queue a knowledge update from a message."""
        await self.update_queue.put(update)

        # Start update task if not running
        if self.update_task is None or self.update_task.done():
            self.update_task = asyncio.create_task(self._process_updates())

    async def _process_updates(self):
        """Process queued knowledge updates."""
        while not self.update_queue.empty():
            try:
                update = await asyncio.wait_for(self.update_queue.get(), timeout=1.0)
                await self._extract_and_store_knowledge(update)
            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.error(f"Failed to process knowledge update: {e}")

    async def _extract_and_store_knowledge(self, update: KnowledgeUpdate):
        """Extract and store knowledge from update."""
        # This is a placeholder for LLM-based extraction
        logger.debug(f"Processing knowledge update from message {update.message_id}")

    async def get_player_info(self, username: str) -> Optional[PlayerInfo]:
        """Get player information from database."""
        entry = await self.crud.read(f"player_{username.lower()}")
        if entry and isinstance(entry.content, PlayerInfo):
            return entry.content
        return None

    async def search_units(
        self,
        category: Optional[str] = None,
        tier: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Unit]:
        """Search for units by criteria."""
        # Get all units
        entries = await self.crud.read_by_type(KnowledgeType.UNIT)

        # Filter results
        results = []
        for entry in entries:
            if isinstance(entry.content, Unit):
                unit = entry.content

                # Apply filters
                if category and unit.category != category:
                    continue
                if tier is not None and unit.tier != tier:
                    continue
                if tags and not any(tag in unit.tags for tag in tags):
                    continue

                results.append(unit)

        return results

    async def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return await self.crud.get_statistics()

    async def close(self):
        """Close any open resources."""
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass