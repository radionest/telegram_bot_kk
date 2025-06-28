# GameKnowledgeService Documentation

## Overview

`GameKnowledgeService` is a comprehensive knowledge management system for War Legends game data. It uses SQLite with JSON storage and full-text search capabilities to store and retrieve game-related information efficiently.

The service is now split into two components:
- **KnowledgeCRUDService**: Handles all database CRUD operations
- **GameKnowledgeService**: Provides business logic and game-specific functionality

## Architecture

### Database Schema

```sql
-- Main knowledge storage table
CREATE TABLE knowledge_entries (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,          -- unit, building, strategy, etc.
    source TEXT NOT NULL,        -- static, dynamic, verified, outdated
    content JSON NOT NULL,       -- Full object data in JSON
    confidence REAL DEFAULT 1.0, -- Relevance confidence score
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    references JSON DEFAULT '[]',
    tags JSON DEFAULT '[]',
    context_tags JSON DEFAULT '[]'
)

-- Full-text search index
CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    id,
    searchable_text,
    content='knowledge_entries',
    content_rowid='rowid'
)
```

### Knowledge Types

- `UNIT` - Game units (infantry, cavalry, ranged, siege)
- `BUILDING` - Game buildings (barracks, stable, workshop)
- `STRATEGY` - Game strategies and build orders
- `MECHANICS` - Game mechanics and formulas
- `PLAYER` - Player information and statistics
- `META` - Meta-game information
- `TIMING` - Timing windows and benchmarks
- `GENERAL` - General game information

### Knowledge Sources

- `STATIC` - Pre-configured knowledge from initialization
- `DYNAMIC` - Extracted from player messages
- `VERIFIED` - Confirmed by multiple sources
- `OUTDATED` - Potentially outdated information

## Usage

### Initialization

```python
from services.game_knowledge_service import GameKnowledgeService

# Create service instance
game_knowledge = GameKnowledgeService(
    db_path=Path("src/knowledge/game_knowledge.db"),
    cache_ttl=3600  # 1 hour cache
)

# Initialize database
await game_knowledge.initialize()
```

### Adding Knowledge

#### Adding Units

```python
from models.game_knowledge import Unit

unit = Unit(
    name="Мечник",
    category="infantry",
    tier=1,
    cost={"gold": 100, "food": 50},
    stats={"attack": 15, "defense": 20, "speed": 3, "health": 100},
    counters=["archer", "siege"],
    countered_by=["cavalry", "spearman"],
    build_time=30,
    description="Базовый пехотинец с хорошей защитой",
    tags=["melee", "tank", "early_game"]
)

await game_knowledge.create_unit(
    unit_id="swordsman",
    unit=unit,
    context_tags=["пехота", "мечники", "танк"]
)
```

#### Adding Buildings

```python
from models.game_knowledge import Building

building = Building(
    name="Казармы",
    category="military",
    max_level=3,
    effects={
        "units_unlocked": ["swordsman", "spearman", "archer"],
        "training_speed_bonus": {1: 0, 2: 0.1, 3: 0.2}
    },
    upgrade_cost={
        2: {"gold": 500, "wood": 300, "stone": 200},
        3: {"gold": 1000, "wood": 600, "stone": 400}
    },
    description="Позволяет тренировать базовую пехоту",
    tags=["military", "essential"]
)

await game_knowledge.create_building(
    building_id="barracks",
    building=building,
    context_tags=["казармы", "военное_здание"]
)
```

#### Adding Strategies

```python
from models.game_knowledge import Strategy

strategy = Strategy(
    name="Лучниковый раш",
    category="rush",
    difficulty="beginner",
    timing_windows=[
        {"time": "3-5 мин", "action": "Построить 2 казармы"},
        {"time": "5-7 мин", "action": "Накопить 10-15 лучников"}
    ],
    unit_composition={"archer": 15, "spearman": 5},
    counters=["turtle_defense", "cavalry_counter"],
    strong_against=["economy_boom"],
    description="Быстрая атака лучниками в начале игры",
    tags=["early_game", "aggressive"]
)

await game_knowledge.create_strategy(
    strategy_id="archer_rush",
    strategy=strategy
)
```

### Retrieving Context

#### Basic Context Retrieval

```python
# Get context for a topic
context = await game_knowledge.get_game_context(
    topic="как защититься от кавалерии",
    limit=5
)
print(context)
# Output: Formatted game context with relevant units, strategies, etc.
```

#### Context with Tags

```python
# Get context with specific tags
context = await game_knowledge.get_game_context(
    topic="атака",
    tags=["cavalry", "rush", "early_game"],
    limit=3
)
```

#### Context with Message History

```python
# Include message context for better relevance
context = await game_knowledge.get_game_context(
    topic="какие юниты лучше",
    message_context="обсуждали стратегию против лучников",
    limit=5
)
```

### Searching Knowledge

#### Search Units

```python
# Find all cavalry units
cavalry_units = await game_knowledge.search_units(category="cavalry")

# Find tier 2 units with specific tags
units = await game_knowledge.search_units(
    tier=2,
    tags=["mobile", "flanking"]
)
```

#### Get Player Info

```python
# Get information about a player
player_info = await game_knowledge.get_player_info("PlayerName")
if player_info:
    print(f"Рейтинг: {player_info.rating}")
    print(f"Предпочитаемые стратегии: {player_info.preferred_strategies}")
```

### Dynamic Knowledge Updates

```python
from models.game_knowledge import KnowledgeUpdate

# Queue knowledge update from a message
update = KnowledgeUpdate(
    message_text="Кавалерия отлично контрит лучников на 5 минуте",
    message_id="msg_123",
    chat_id=12345,
    username="ProPlayer",
    timestamp=datetime.now(),
    topic_tags=["strategy", "cavalry"]
)

await game_knowledge.update_knowledge_from_message(update)
```

## Integration with LiteLLMClient

```python
from utils.litellm_client import LiteLLMClient

# Initialize with game knowledge
litellm_client = LiteLLMClient(
    config_path="litellm_models.yaml",
    game_knowledge_service=game_knowledge
)

# Context will be automatically included in prompts
response = await litellm_client.generate_free_response(
    message="как победить кавалерию?",
    chat_id=12345
)
```

## Context Format Example

When retrieving context, the service returns formatted text like:

```
=== КОНТЕКСТ ИГРЫ WAR LEGENDS ===

ЮНИТЫ:
- Копейщик (infantry, Уровень 1)
  Статы: attack: 12, defense: 18, speed: 3, health: 90
  Сильна против: cavalry, halberdier
  Слаба против: archer, swordsman
  Специализируется на борьбе с кавалерией

СТРАТЕГИИ:
- Защита копьями (defensive, Сложность: beginner)
  Построение стены из копейщиков против кавалерийских атак
  Состав армии: spearman: 20, archer: 10
  Эффективна против: cavalry_rush, knight_charge
```

## Performance Considerations

1. **Caching**: Context results are cached for `cache_ttl` seconds (default: 3600)
2. **Full-Text Search**: Uses SQLite FTS5 for efficient text searching
3. **Batch Operations**: Use `add_knowledge_entries()` for bulk inserts
4. **Async Operations**: All database operations are asynchronous

## Best Practices

1. **Tag Usage**:
   - Use English tags for technical classification (e.g., "early_game", "rush")
   - Use Russian context_tags for natural language matching
   - Keep tags consistent across similar content

2. **Content Organization**:
   - Group related knowledge by type
   - Use descriptive IDs (e.g., "archer_rush", not "strategy_1")
   - Maintain confidence scores for dynamic content

3. **Search Optimization**:
   - Provide specific topics for better relevance
   - Use tags to narrow down search results
   - Include message context when available

4. **Memory Management**:
   - Clear cache periodically if running for long periods
   - Close service properly with `await game_knowledge.close()`

## Error Handling

```python
try:
    context = await game_knowledge.get_game_context("topic")
except Exception as e:
    logger.error(f"Failed to get game context: {e}")
    # Fallback to general game info
    context = game_knowledge._get_general_game_info()
```

## KnowledgeCRUDService API

The CRUD service provides low-level database operations:

### Basic CRUD Operations

```python
from services.knowledge_crud_service import KnowledgeCRUDService

crud = KnowledgeCRUDService()

# Create
success = await crud.create(entry)
count = await crud.create_batch(entries)

# Read
entry = await crud.read(entry_id)
entries = await crud.read_by_type(KnowledgeType.UNIT, limit=10)

# Update
success = await crud.update(entry_id, {"confidence": 0.8})

# Delete
success = await crud.delete(entry_id)
```

### Advanced Search

```python
# Full-text search
results = await crud.search_fts("кавалерия атака", limit=10)

# Search by tags
results = await crud.search_by_tags(["cavalry", "rush"], match_all=True)

# Get statistics
stats = await crud.get_statistics()
```

## Future Enhancements

1. **Vector Search**: Add embedding-based semantic search
2. **Knowledge Validation**: Verify dynamic knowledge against static rules
3. **Conflict Resolution**: Handle contradicting information
4. **Knowledge Decay**: Automatically mark old dynamic knowledge as outdated
5. **Export/Import**: Backup and restore knowledge base
6. **Advanced Analytics**: Track knowledge usage and effectiveness