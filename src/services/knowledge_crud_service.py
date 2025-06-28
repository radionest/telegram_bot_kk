"""CRUD service for War Legends knowledge database operations."""

import json
import aiosqlite
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import asdict, is_dataclass

from loguru import logger

from models.game_knowledge import (
    KnowledgeEntry,
    KnowledgeType,
    KnowledgeSource,
    Unit,
    Building,
    Strategy,
    PlayerInfo,
    GameMechanic,
)


class KnowledgeCRUDService:
    """Service for CRUD operations on knowledge database."""

    def __init__(self, db_path: Path = Path("src/knowledge/game_knowledge.db")):
        """Initialize CRUD service.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

    async def initialize_database(self):
        """Create database tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content JSON NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    references JSON DEFAULT '[]',
                    tags JSON DEFAULT '[]',
                    context_tags JSON DEFAULT '[]'
                )
            """)

            # Create indexes for efficient querying
            await db.execute("CREATE INDEX IF NOT EXISTS idx_type ON knowledge_entries(type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_source ON knowledge_entries(source)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON knowledge_entries(confidence)")

            # Create full-text search virtual table
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    id,
                    searchable_text,
                    content='knowledge_entries',
                    content_rowid='rowid'
                )
            """)

            await db.commit()

    async def create(self, entry: KnowledgeEntry) -> bool:
        """Create a single knowledge entry.

        Args:
            entry: KnowledgeEntry to create

        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO knowledge_entries
                    (id, type, source, content, confidence, created_at, updated_at, references, tags, context_tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.type.value,
                    entry.source.value,
                    json.dumps(self._serialize_content(entry.content)),
                    entry.confidence,
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                    json.dumps(entry.references),
                    json.dumps(entry.tags),
                    json.dumps(entry.context_tags),
                ))

                # Update FTS index
                searchable_text = self._get_searchable_text(entry)
                await db.execute("""
                    INSERT OR REPLACE INTO knowledge_fts (id, searchable_text)
                    VALUES (?, ?)
                """, (entry.id, searchable_text))

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to create entry {entry.id}: {e}")
            return False

    async def create_batch(self, entries: List[KnowledgeEntry]) -> int:
        """Create multiple knowledge entries.

        Args:
            entries: List of KnowledgeEntry to create

        Returns:
            Number of successfully created entries
        """
        if not entries:
            return 0

        async with aiosqlite.connect(self.db_path) as db:
            # Prepare data for insertion
            rows = []
            fts_rows = []

            for entry in entries:
                rows.append((
                    entry.id,
                    entry.type.value,
                    entry.source.value,
                    json.dumps(self._serialize_content(entry.content)),
                    entry.confidence,
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                    json.dumps(entry.references),
                    json.dumps(entry.tags),
                    json.dumps(entry.context_tags),
                ))

                fts_rows.append((
                    entry.id,
                    self._get_searchable_text(entry),
                ))

            # Insert into main table
            await db.executemany("""
                INSERT OR REPLACE INTO knowledge_entries
                (id, type, source, content, confidence, created_at, updated_at, references, tags, context_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            # Update FTS index
            await db.executemany("""
                INSERT OR REPLACE INTO knowledge_fts (id, searchable_text)
                VALUES (?, ?)
            """, fts_rows)

            await db.commit()
            return len(entries)

    async def read(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Read a single knowledge entry by ID.

        Args:
            entry_id: ID of the entry to read

        Returns:
            KnowledgeEntry if found, None otherwise
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("""
                SELECT * FROM knowledge_entries WHERE id = ?
            """, (entry_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_entry(row)
        return None

    async def read_by_type(
        self,
        knowledge_type: KnowledgeType,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[KnowledgeEntry]:
        """Read entries by type.

        Args:
            knowledge_type: Type of knowledge to retrieve
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of KnowledgeEntry
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            query = """
                SELECT * FROM knowledge_entries
                WHERE type = ?
                ORDER BY confidence DESC, updated_at DESC
            """
            params = [knowledge_type.value]

            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            results = []
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    entry = self._row_to_entry(row)
                    if entry:
                        results.append(entry)

            return results

    async def update(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a knowledge entry.

        Args:
            entry_id: ID of the entry to update
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get existing entry
            existing = await self.read(entry_id)
            if not existing:
                logger.warning(f"Entry {entry_id} not found for update")
                return False

            # Prepare update fields
            update_fields = []
            update_values = []

            # Handle special fields
            if "content" in updates:
                update_fields.append("content = ?")
                update_values.append(json.dumps(self._serialize_content(updates["content"])))

            if "confidence" in updates:
                update_fields.append("confidence = ?")
                update_values.append(updates["confidence"])

            if "source" in updates:
                update_fields.append("source = ?")
                update_values.append(updates["source"].value if hasattr(updates["source"], "value") else updates["source"])

            if "tags" in updates:
                update_fields.append("tags = ?")
                update_values.append(json.dumps(updates["tags"]))

            if "context_tags" in updates:
                update_fields.append("context_tags = ?")
                update_values.append(json.dumps(updates["context_tags"]))

            if "references" in updates:
                update_fields.append("references = ?")
                update_values.append(json.dumps(updates["references"]))

            # Always update timestamp
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now().isoformat())

            # Add entry_id for WHERE clause
            update_values.append(entry_id)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(f"""
                    UPDATE knowledge_entries
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, update_values)

                # Update FTS if content changed
                if "content" in updates:
                    # Create temporary entry for searchable text extraction
                    temp_entry = KnowledgeEntry(
                        id=entry_id,
                        type=existing.type,
                        source=existing.source,
                        content=updates["content"],
                        tags=updates.get("tags", existing.tags),
                        context_tags=updates.get("context_tags", existing.context_tags),
                    )
                    searchable_text = self._get_searchable_text(temp_entry)

                    await db.execute("""
                        UPDATE knowledge_fts
                        SET searchable_text = ?
                        WHERE id = ?
                    """, (searchable_text, entry_id))

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """Delete a knowledge entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Delete from main table
                await db.execute("DELETE FROM knowledge_entries WHERE id = ?", (entry_id,))

                # Delete from FTS index
                await db.execute("DELETE FROM knowledge_fts WHERE id = ?", (entry_id,))

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            return False

    async def search_fts(
        self,
        query: str,
        limit: int = 10,
        types: Optional[List[KnowledgeType]] = None
    ) -> List[KnowledgeEntry]:
        """Search entries using full-text search.

        Args:
            query: Search query
            limit: Maximum number of results
            types: Optional list of types to filter

        Returns:
            List of matching KnowledgeEntry
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Build type filter
            type_filter = ""
            params = [query, limit]

            if types:
                type_placeholders = ','.join('?' * len(types))
                type_filter = f" AND ke.type IN ({type_placeholders})"
                params = [query] + [t.value for t in types] + [limit]

            results = []
            async with db.execute(f"""
                SELECT ke.*
                FROM knowledge_entries ke
                JOIN knowledge_fts kf ON ke.id = kf.id
                WHERE knowledge_fts MATCH ?{type_filter}
                ORDER BY rank
                LIMIT ?
            """, params) as cursor:
                async for row in cursor:
                    entry = self._row_to_entry(row)
                    if entry:
                        results.append(entry)

            return results

    async def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 10
    ) -> List[KnowledgeEntry]:
        """Search entries by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, entries must have all tags; if False, any tag
            limit: Maximum number of results

        Returns:
            List of matching KnowledgeEntry
        """
        if not tags:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if match_all:
                # Build conditions for all tags
                tag_conditions = []
                params = []
                for tag in tags:
                    tag_conditions.append("(tags LIKE ? OR context_tags LIKE ?)")
                    params.extend([f'%"{tag}"%', f'%"{tag}"%'])

                query = f"""
                    SELECT * FROM knowledge_entries
                    WHERE {' AND '.join(tag_conditions)}
                    ORDER BY confidence DESC
                    LIMIT ?
                """
                params.append(limit)
            else:
                # Build conditions for any tag
                tag_conditions = []
                params = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ? OR context_tags LIKE ?")
                    params.extend([f'%"{tag}"%', f'%"{tag}"%'])

                query = f"""
                    SELECT * FROM knowledge_entries
                    WHERE {' OR '.join(tag_conditions)}
                    ORDER BY confidence DESC
                    LIMIT ?
                """
                params.append(limit)

            results = []
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    entry = self._row_to_entry(row)
                    if entry:
                        results.append(entry)

            return results

    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}

            # Total entries
            async with db.execute("SELECT COUNT(*) FROM knowledge_entries") as cursor:
                stats["total_entries"] = (await cursor.fetchone())[0]

            # Entries by type
            async with db.execute("""
                SELECT type, COUNT(*) as count
                FROM knowledge_entries
                GROUP BY type
            """) as cursor:
                stats["by_type"] = {row[0]: row[1] async for row in cursor}

            # Entries by source
            async with db.execute("""
                SELECT source, COUNT(*) as count
                FROM knowledge_entries
                GROUP BY source
            """) as cursor:
                stats["by_source"] = {row[0]: row[1] async for row in cursor}

            # Average confidence
            async with db.execute("SELECT AVG(confidence) FROM knowledge_entries") as cursor:
                stats["avg_confidence"] = (await cursor.fetchone())[0] or 0.0

            # Recent updates
            async with db.execute("""
                SELECT COUNT(*) FROM knowledge_entries
                WHERE datetime(updated_at) > datetime('now', '-1 day')
            """) as cursor:
                stats["recent_updates"] = (await cursor.fetchone())[0]

            return stats

    def _serialize_content(self, content: Any) -> Dict[str, Any]:
        """Serialize content object to dictionary."""
        if is_dataclass(content):
            return asdict(content)
        elif isinstance(content, dict):
            return content
        return {"raw": str(content)}

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

    def _row_to_entry(self, row: aiosqlite.Row) -> Optional[KnowledgeEntry]:
        """Convert database row to KnowledgeEntry."""
        try:
            # Parse content based on type
            content_data = json.loads(row["content"])
            knowledge_type = KnowledgeType(row["type"])

            # Reconstruct the appropriate content object
            if knowledge_type == KnowledgeType.UNIT:
                content = Unit(**content_data)
            elif knowledge_type == KnowledgeType.BUILDING:
                content = Building(**content_data)
            elif knowledge_type == KnowledgeType.STRATEGY:
                content = Strategy(**content_data)
            elif knowledge_type == KnowledgeType.MECHANICS:
                content = GameMechanic(**content_data)
            elif knowledge_type == KnowledgeType.PLAYER:
                content = PlayerInfo(**content_data)
            else:
                content = content_data

            return KnowledgeEntry(
                id=row["id"],
                type=knowledge_type,
                source=KnowledgeSource(row["source"]),
                content=content,
                confidence=row["confidence"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                references=json.loads(row["references"]),
                tags=json.loads(row["tags"]),
                context_tags=json.loads(row["context_tags"]),
            )
        except Exception as e:
            logger.error(f"Failed to parse row {row['id']}: {e}")
            return None