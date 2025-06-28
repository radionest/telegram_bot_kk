"""CRUD service for game knowledge using ChromaDB vector database."""

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json
from loguru import logger

from src.models.game_knowledge_chromadb import (
    ChromaDocument, ChromaSearchResult, KnowledgeType, KnowledgeSource
)


class ChromaKnowledgeCRUD:
    """Low-level CRUD operations for knowledge entries using ChromaDB."""
    
    def __init__(
        self,
        persist_directory: str = "./data/chromadb",
        collection_name: str = "game_knowledge",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_name: Name of the collection
            embedding_model: Model to use for embeddings
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.client = None
        self.collection = None
        self.embedding_function = None
    
    async def initialize(self):
        """Асинхронная инициализация ChromaDB клиента."""
        # Создаем асинхронный клиент ChromaDB
        self.client = await chromadb.AsyncPersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Создаем embedding function
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )
        
        # Получаем или создаем коллекцию
        try:
            self.collection = await self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "War Legends game knowledge base"}
            )
            logger.info(f"Created new ChromaDB collection: {self.collection_name}")
        except:
            self.collection = await self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Using existing ChromaDB collection: {self.collection_name}")
    
    async def create(self, document: ChromaDocument) -> bool:
        """
        Create a new knowledge entry.
        
        Args:
            document: ChromaDocument to store
            
        Returns:
            True if successful
        """
        try:
            await self.collection.add(
                documents=[document.document],
                metadatas=[document.metadata],
                ids=[document.id]
            )
            logger.debug(f"Created knowledge entry: {document.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create entry {document.id}: {e}")
            return False
    
    async def get(self, entry_id: str) -> Optional[ChromaSearchResult]:
        """
        Get a knowledge entry by ID.
        
        Args:
            entry_id: Unique identifier
            
        Returns:
            ChromaSearchResult or None if not found
        """
        try:
            result = await self.collection.get(ids=[entry_id])
            
            if not result['ids']:
                return None
            
            return ChromaSearchResult(
                id=result['ids'][0],
                document=result['documents'][0] if result.get('documents') else '',
                metadata=result['metadatas'][0],
                distance=0.0  # При прямом получении по ID расстояние = 0
            )
        except Exception as e:
            logger.error(f"Failed to get entry {entry_id}: {e}")
            return None
    
    async def update(self, document: ChromaDocument) -> bool:
        """
        Update an existing knowledge entry.
        
        Args:
            document: Updated ChromaDocument
            
        Returns:
            True if successful
        """
        try:
            # Обновляем timestamp
            document.metadata['updated_at'] = datetime.now().isoformat()
            
            await self.collection.update(
                documents=[document.document],
                metadatas=[document.metadata],
                ids=[document.id]
            )
            logger.debug(f"Updated knowledge entry: {document.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update entry {document.id}: {e}")
            return False
    
    async def delete(self, entry_id: str) -> bool:
        """
        Delete a knowledge entry.
        
        Args:
            entry_id: ID to delete
            
        Returns:
            True if successful
        """
        try:
            await self.collection.delete(ids=[entry_id])
            logger.debug(f"Deleted knowledge entry: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {e}")
            return False
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> List[ChromaSearchResult]:
        """
        Search for knowledge entries using vector similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            where: Metadata filters (e.g., {"type": "unit"})
            where_document: Document content filters
            
        Returns:
            List of search results sorted by relevance
        """
        try:
            results = await self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
                where_document=where_document
            )
            
            search_results = []
            if results['ids'] and results['ids'][0]:  # Проверяем что есть результаты
                for i in range(len(results['ids'][0])):
                    search_results.append(ChromaSearchResult(
                        id=results['ids'][0][i],
                        document=results['documents'][0][i] if results.get('documents') else '',
                        metadata=results['metadatas'][0][i],
                        distance=results['distances'][0][i]
                    ))
            
            return search_results
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    async def search_by_type(
        self,
        knowledge_type: KnowledgeType,
        query: Optional[str] = None,
        limit: int = 10,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[ChromaSearchResult]:
        """
        Search within a specific knowledge type.
        
        Args:
            knowledge_type: Type to filter by
            query: Optional search query
            limit: Maximum results
            additional_filters: Extra metadata filters
            
        Returns:
            Filtered search results
        """
        where = {"type": knowledge_type.value}
        if additional_filters:
            where.update(additional_filters)
        
        if query:
            return await self.search(query, limit, where)
        else:
            # Если нет query, получаем все документы данного типа
            try:
                results = await self.collection.get(
                    where=where,
                    limit=limit,
                    include=["metadatas", "documents", "distances"]
                )
                
                search_results = []
                for i in range(len(results['ids'])):
                    search_results.append(ChromaSearchResult(
                        id=results['ids'][i],
                        document=results['documents'][i] if results.get('documents') else '',
                        metadata=results['metadatas'][i],
                        distance=0.0
                    ))
                
                return search_results
            except Exception as e:
                logger.error(f"Failed to get entries by type {knowledge_type}: {e}")
                return []
    
    async def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 10
    ) -> List[ChromaSearchResult]:
        """
        Search entries by tags.
        
        Args:
            tags: Tags to search for
            match_all: If True, entry must have all tags
            limit: Maximum results
            
        Returns:
            Entries matching tag criteria
        """
        if match_all:
            # ChromaDB не поддерживает прямой $all оператор,
            # придется фильтровать результаты вручную
            results = await self.collection.get(
                limit=limit * 3,  # Берем больше для фильтрации
                include=["metadatas", "documents"]
            )
            
            filtered = []
            for i in range(len(results['ids'])):
                entry_tags = results['metadatas'][i].get('tags', [])
                if all(tag in entry_tags for tag in tags):
                    filtered.append(ChromaSearchResult(
                        id=results['ids'][i],
                        document=results['documents'][i] if results.get('documents') else '',
                        metadata=results['metadatas'][i],
                        distance=0.0
                    ))
                    if len(filtered) >= limit:
                        break
            
            return filtered
        else:
            # Для OR условия создаем запрос поиска по тегам
            # ChromaDB поддерживает $contains для массивов
            where = {"$or": [{"tags": {"$contains": tag}} for tag in tags]}
            
            results = await self.collection.get(
                where=where,
                limit=limit,
                include=["metadatas", "documents"]
            )
            
            search_results = []
            for i in range(len(results['ids'])):
                search_results.append(ChromaSearchResult(
                    id=results['ids'][i],
                    document=results['documents'][i] if results.get('documents') else '',
                    metadata=results['metadatas'][i],
                    distance=0.0
                ))
            
            return search_results
    
    async def update_confidence(self, entry_id: str, confidence: float) -> bool:
        """
        Update confidence score for an entry.
        
        Args:
            entry_id: Entry to update
            confidence: New confidence value (0.0 to 1.0)
            
        Returns:
            True if successful
        """
        entry = await self.get(entry_id)
        if not entry:
            return False
        
        entry.metadata['confidence'] = confidence
        entry.metadata['updated_at'] = datetime.now().isoformat()
        
        return await self.update(ChromaDocument(
            id=entry.id,
            document=entry.document,
            metadata=entry.metadata
        ))
    
    async def add_reference(self, entry_id: str, reference: str) -> bool:
        """
        Add a reference to an entry.
        
        Args:
            entry_id: Entry to update
            reference: Reference to add (e.g., message ID)
            
        Returns:
            True if successful
        """
        entry = await self.get(entry_id)
        if not entry:
            return False
        
        references = entry.metadata.get('references', [])
        if reference not in references:
            references.append(reference)
            entry.metadata['references'] = references
            entry.metadata['updated_at'] = datetime.now().isoformat()
            
            return await self.update(ChromaDocument(
                id=entry.id,
                document=entry.document,
                metadata=entry.metadata
            ))
        
        return True
    
    async def bulk_create(self, documents: List[ChromaDocument]) -> int:
        """
        Create multiple entries at once.
        
        Args:
            documents: List of ChromaDocuments to create
            
        Returns:
            Number of successfully created entries
        """
        if not documents:
            return 0
        
        try:
            await self.collection.add(
                documents=[doc.document for doc in documents],
                metadatas=[doc.metadata for doc in documents],
                ids=[doc.id for doc in documents]
            )
            logger.info(f"Bulk created {len(documents)} knowledge entries")
            return len(documents)
        except Exception as e:
            logger.error(f"Failed to bulk create entries: {e}")
            return 0
    
    async def count_by_type(self, knowledge_type: Optional[KnowledgeType] = None) -> int:
        """
        Count entries by type.
        
        Args:
            knowledge_type: Type to count, or None for all
            
        Returns:
            Number of entries
        """
        where = {"type": knowledge_type.value} if knowledge_type else None
        
        try:
            if where:
                result = await self.collection.get(where=where)
                return len(result['ids'])
            else:
                # Для подсчета всех документов используем count()
                return await self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count entries: {e}")
            return 0
    
    async def reset_collection(self) -> bool:
        """
        Delete and recreate the collection.
        WARNING: This will delete all data!
        
        Returns:
            True if successful
        """
        try:
            await self.client.delete_collection(self.collection_name)
            self.collection = await self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "War Legends game knowledge base"}
            )
            logger.warning(f"Reset ChromaDB collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
    
    async def close(self):
        """Cleanup resources."""
        # ChromaDB async client не требует явного закрытия
        pass