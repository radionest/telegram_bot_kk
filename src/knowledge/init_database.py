"""Initialize War Legends knowledge database with initial data."""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from loguru import logger

from services.game_knowledge_service import GameKnowledgeService
from models.game_knowledge import (
    Unit, Building, Strategy, GameMechanic,
    KnowledgeSource
)


async def initialize_units(service: GameKnowledgeService):
    """Initialize unit data."""
    units_data = [
        {
            "id": "swordsman",
            "unit": Unit(
                name="Мечник",
                category="infantry",
                tier=1,
                cost={"gold": 100, "food": 50},
                stats={"attack": 15, "defense": 20, "speed": 3, "health": 100},
                counters=["archer", "siege"],
                countered_by=["cavalry", "spearman"],
                special_abilities=[],
                build_time=30,
                description="Базовый пехотинец с хорошей защитой",
                tags=["melee", "tank", "early_game"],
            ),
            "context_tags": ["пехота", "мечники", "танк"],
        },
        {
            "id": "archer",
            "unit": Unit(
                name="Лучник",
                category="ranged",
                tier=1,
                cost={"gold": 120, "wood": 60},
                stats={"attack": 18, "defense": 8, "speed": 4, "health": 60, "range": 5},
                counters=["spearman", "cavalry"],
                countered_by=["swordsman", "siege"],
                special_abilities=["ranged_attack"],
                build_time=25,
                description="Дальнобойный юнит с низкой защитой",
                tags=["ranged", "dps", "early_game"],
            ),
            "context_tags": ["стрелки", "лучники", "дальний_бой"],
        },
        {
            "id": "cavalry",
            "unit": Unit(
                name="Кавалерия",
                category="cavalry",
                tier=2,
                cost={"gold": 200, "food": 100},
                stats={"attack": 25, "defense": 15, "speed": 7, "health": 150},
                counters=["archer", "siege", "swordsman"],
                countered_by=["spearman", "halberdier"],
                special_abilities=["charge", "mobile"],
                build_time=45,
                description="Быстрые юниты, эффективны против стрелков",
                tags=["mobile", "flanking", "mid_game"],
            ),
            "context_tags": ["кавалерия", "всадники", "конница"],
        },
        {
            "id": "spearman",
            "unit": Unit(
                name="Копейщик",
                category="infantry",
                tier=1,
                cost={"gold": 80, "wood": 40},
                stats={"attack": 12, "defense": 18, "speed": 3, "health": 90},
                counters=["cavalry", "halberdier"],
                countered_by=["archer", "swordsman"],
                special_abilities=["anti_cavalry"],
                build_time=25,
                description="Специализируется на борьбе с кавалерией",
                tags=["anti_cavalry", "defensive", "early_game"],
            ),
            "context_tags": ["копейщики", "антикавалерия", "пехота"],
        },
        {
            "id": "catapult",
            "unit": Unit(
                name="Катапульта",
                category="siege",
                tier=3,
                cost={"gold": 400, "wood": 200, "stone": 100},
                stats={"attack": 50, "defense": 5, "speed": 1, "health": 200, "range": 8},
                counters=["buildings", "infantry_groups"],
                countered_by=["cavalry", "fast_units"],
                special_abilities=["siege_damage", "area_damage"],
                build_time=90,
                description="Осадное орудие для разрушения зданий",
                tags=["siege", "late_game", "anti_building"],
            ),
            "context_tags": ["осада", "катапульта", "разрушение"],
        },
        {
            "id": "knight",
            "unit": Unit(
                name="Рыцарь",
                category="cavalry",
                tier=3,
                cost={"gold": 350, "food": 150, "iron": 50},
                stats={"attack": 35, "defense": 25, "speed": 6, "health": 250},
                counters=["archer", "light_infantry"],
                countered_by=["halberdier", "heavy_spearman"],
                special_abilities=["heavy_armor", "charge"],
                build_time=60,
                description="Элитная тяжелая кавалерия",
                tags=["elite", "heavy", "late_game"],
            ),
            "context_tags": ["рыцари", "элита", "тяжелая_кавалерия"],
        },
    ]

    logger.info(f"Initializing {len(units_data)} units...")
    for unit_data in units_data:
        await service.create_unit(
            unit_id=unit_data["id"],
            unit=unit_data["unit"],
            source=KnowledgeSource.STATIC,
            context_tags=unit_data["context_tags"],
        )


async def initialize_buildings(service: GameKnowledgeService):
    """Initialize building data."""
    buildings_data = [
        {
            "id": "barracks",
            "building": Building(
                name="Казармы",
                category="military",
                max_level=3,
                effects={
                    "units_unlocked": ["swordsman", "spearman", "archer"],
                    "training_speed_bonus": {1: 0, 2: 0.1, 3: 0.2},
                },
                upgrade_cost={
                    2: {"gold": 500, "wood": 300, "stone": 200},
                    3: {"gold": 1000, "wood": 600, "stone": 400},
                },
                upgrade_time={2: 300, 3: 600},
                prerequisites=[],
                description="Позволяет тренировать базовую пехоту",
                tags=["military", "essential"],
            ),
            "context_tags": ["казармы", "военное_здание", "пехота"],
        },
        {
            "id": "stable",
            "building": Building(
                name="Конюшня",
                category="military",
                max_level=3,
                effects={
                    "units_unlocked": ["cavalry", "knight"],
                    "cavalry_speed_bonus": {1: 0, 2: 0.05, 3: 0.1},
                },
                upgrade_cost={
                    2: {"gold": 700, "wood": 400, "food": 300},
                    3: {"gold": 1400, "wood": 800, "food": 600},
                },
                upgrade_time={2: 400, 3: 800},
                prerequisites=["barracks"],
                description="Позволяет тренировать кавалерию",
                tags=["military", "cavalry"],
            ),
            "context_tags": ["конюшня", "кавалерия", "военное_здание"],
        },
        {
            "id": "workshop",
            "building": Building(
                name="Мастерская",
                category="military",
                max_level=2,
                effects={
                    "units_unlocked": ["catapult", "ballista"],
                    "siege_damage_bonus": {1: 0, 2: 0.15},
                },
                upgrade_cost={
                    2: {"gold": 1000, "wood": 800, "stone": 600, "iron": 200},
                },
                upgrade_time={2: 600},
                prerequisites=["barracks", "blacksmith"],
                description="Позволяет строить осадные орудия",
                tags=["military", "siege", "late_game"],
            ),
            "context_tags": ["мастерская", "осада", "осадные_орудия"],
        },
    ]

    logger.info(f"Initializing {len(buildings_data)} buildings...")
    for building_data in buildings_data:
        await service.create_building(
            building_id=building_data["id"],
            building=building_data["building"],
            source=KnowledgeSource.STATIC,
            context_tags=building_data["context_tags"],
        )


async def initialize_strategies(service: GameKnowledgeService):
    """Initialize strategy data."""
    strategies_data = [
        {
            "id": "archer_rush",
            "strategy": Strategy(
                name="Лучниковый раш",
                category="rush",
                difficulty="beginner",
                timing_windows=[
                    {"time": "3-5 мин", "action": "Построить 2 казармы"},
                    {"time": "5-7 мин", "action": "Накопить 10-15 лучников"},
                    {"time": "7-10 мин", "action": "Атаковать противника"},
                ],
                unit_composition={"archer": 15, "spearman": 5},
                building_priorities=["barracks", "archery_range", "economy"],
                counters=["turtle_defense", "cavalry_counter"],
                strong_against=["economy_boom", "late_game_strategies"],
                description="Быстрая атака лучниками в начале игры",
                tips=[
                    "Фокусируйтесь на экономике дерева",
                    "Атакуйте рабочих противника",
                    "Отступайте при появлении кавалерии",
                ],
                tags=["early_game", "aggressive", "micro_intensive"],
            ),
            "context_tags": ["раш", "лучники", "ранняя_атака"],
        },
        {
            "id": "cavalry_flanking",
            "strategy": Strategy(
                name="Кавалерийский фланг",
                category="hybrid",
                difficulty="intermediate",
                timing_windows=[
                    {"time": "5-7 мин", "action": "Построить конюшню"},
                    {"time": "8-10 мин", "action": "Накопить 5-7 кавалерии"},
                    {"time": "10-12 мин", "action": "Обход с флангов"},
                ],
                unit_composition={"cavalry": 10, "swordsman": 15, "archer": 10},
                building_priorities=["barracks", "stable", "blacksmith"],
                counters=["spear_wall", "defensive_towers"],
                strong_against=["archer_armies", "economy_focused"],
                description="Комбинированная атака с обходом кавалерией",
                tips=[
                    "Используйте пехоту для отвлечения",
                    "Атакуйте лучников с тыла кавалерией",
                    "Избегайте копейщиков",
                ],
                tags=["mid_game", "mobile", "flanking"],
            ),
            "context_tags": ["кавалерия", "фланг", "маневр"],
        },
    ]

    logger.info(f"Initializing {len(strategies_data)} strategies...")
    for strategy_data in strategies_data:
        await service.create_strategy(
            strategy_id=strategy_data["id"],
            strategy=strategy_data["strategy"],
            source=KnowledgeSource.STATIC,
            context_tags=strategy_data["context_tags"],
        )


async def initialize_mechanics(service: GameKnowledgeService):
    """Initialize game mechanics data."""
    mechanics_data = [
        {
            "id": "damage_calculation",
            "mechanic": GameMechanic(
                name="Расчет урона",
                category="combat",
                description="Урон рассчитывается с учетом атаки нападающего, защиты защищающегося и бонусов типов юнитов",
                formula="damage = (attack * type_bonus) - (defense * 0.5)",
                examples=[
                    "Лучник (18 атаки) vs Мечник (20 защиты): 18 - 10 = 8 урона",
                    "Кавалерия (25 атаки) vs Лучник (8 защиты) с бонусом x1.5: 37.5 - 4 = 33.5 урона",
                ],
                related_mechanics=["type_bonuses", "armor_types"],
                tips=[
                    "Используйте юниты с бонусами против типов врага",
                    "Защита снижает входящий урон на 50%",
                ],
                tags=["combat", "damage", "calculations"],
            ),
            "context_tags": ["урон", "бой", "механика"],
        },
        {
            "id": "economy_growth",
            "mechanic": GameMechanic(
                name="Рост экономики",
                category="economy",
                description="Экономика растет за счет рабочих, собирающих ресурсы, и бонусов от зданий",
                formula="income_rate = workers * efficiency * building_bonus",
                examples=[
                    "10 рабочих на золоте с эффективностью 1.0: 10 золота/мин",
                    "15 рабочих на дереве с мельницей (+20%): 18 дерева/мин",
                ],
                related_mechanics=["worker_efficiency", "building_bonuses"],
                tips=[
                    "Поддерживайте баланс между военными расходами и экономикой",
                    "Стройте экономические здания для увеличения дохода",
                ],
                tags=["economy", "resources", "management"],
            ),
            "context_tags": ["экономика", "ресурсы", "доход"],
        },
    ]

    logger.info(f"Initializing {len(mechanics_data)} game mechanics...")
    for mechanic_data in mechanics_data:
        await service.create_mechanic(
            mechanic_id=mechanic_data["id"],
            mechanic=mechanic_data["mechanic"],
            source=KnowledgeSource.STATIC,
            context_tags=mechanic_data["context_tags"],
        )


async def main():
    """Main initialization function."""
    logger.info("Starting War Legends knowledge database initialization...")
    
    # Create service
    service = GameKnowledgeService()
    
    # Initialize database
    await service.initialize()
    
    # Initialize all data
    await initialize_units(service)
    await initialize_buildings(service)
    await initialize_strategies(service)
    await initialize_mechanics(service)
    
    logger.info("Knowledge database initialization completed!")
    
    # Test search
    logger.info("\nTesting search functionality...")
    context = await service.get_game_context("кавалерия атака", limit=3)
    logger.info(f"Search results:\n{context}")
    
    # Get and display statistics
    stats = await service.get_statistics()
    logger.info(f"\nDatabase statistics: {stats}")
    
    await service.close()


if __name__ == "__main__":
    asyncio.run(main())