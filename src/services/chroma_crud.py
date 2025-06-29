from typing import List, Optional, Dict, Any
import chromadb
from chromadb.utils import embedding_functions
from loguru import logger

from models.base_document import BaseDocument
from exceptions import (
    ChromaInitializationError,
    ChromaDocumentError,
    ChromaSearchError,
    ChromaValidationError,
)


class ChromaCRUD:
    """Универсальный CRUD сервис для работы с ChromaDB."""

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.embedding_model = embedding_model
        self._client: Optional[chromadb.AsyncClientAPI] = None
        self._collections: Dict[str, Any] = {}
        self._embedding_function = None

    async def _ensure_client(self):
        """Обеспечивает наличие инициализированного клиента."""
        if self._client is None:
            try:
                self._client = await chromadb.AsyncHttpClient(
                    host='localhost',
                    port=self.chroma_port)
            except Exception as e:
                logger.error(f"Не удалось инициализировать ChromaDB клиент: {e}")
                raise ChromaInitializationError(
                    f"Failed to initialize ChromaDB client: {e}"
                )

            self._embedding_function = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.embedding_model
                )
            )
            logger.info("ChromaDB клиент инициализирован")

    async def _get_collection(self, collection_name: str):
        """Получает или создает коллекцию по имени."""
        await self._ensure_client()

        if collection_name not in self._collections:
            try:
                self._collections[
                    collection_name
                ] = await self._client.get_or_create_collection(  # type: ignore
                    name=collection_name, embedding_function=self._embedding_function
                )
                logger.info(f"Коллекция '{collection_name}' создана/получена")
            except Exception as e:
                logger.error(
                    f"Не удалось создать/получить коллекцию '{collection_name}': {e}"
                )
                raise ChromaInitializationError(
                    f"Failed to get/create collection '{collection_name}': {e}"
                )

        return self._collections[collection_name]

    async def add(self, document: BaseDocument, collection_name: str) -> bool:
        """Добавляет документ в ChromaDB."""
        collection = await self._get_collection(collection_name)

        document_id = document.get_document_id()
        text_content = document.get_text_content()

        if not text_content.strip():
            raise ChromaValidationError(
                f"Document {document_id} has empty text content"
            )

        try:
            await collection.add(
                documents=[text_content],
                metadatas=[document.to_metadata()],
                ids=[document_id],
            )
        except Exception as e:
            logger.error(
                f"Ошибка при добавлении документа {document_id} в коллекцию '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to add document {document_id}: {e}")

        logger.debug(f"Документ {document_id} добавлен в коллекцию '{collection_name}'")
        return True

    async def add_batch(
        self, documents: List[BaseDocument], collection_name: str
    ) -> int:
        """Добавляет пакет документов в ChromaDB."""
        collection = await self._get_collection(collection_name)

        valid_documents = [d for d in documents if d.get_text_content().strip()]

        if not valid_documents:
            raise ChromaValidationError("No documents with text content to add")

        documents_text = [d.get_text_content() for d in valid_documents]
        metadatas = [d.to_metadata() for d in valid_documents]
        ids = [d.get_document_id() for d in valid_documents]

        try:
            await collection.add(documents=documents_text, metadatas=metadatas, ids=ids)
        except Exception as e:
            logger.error(
                f"Ошибка при пакетном добавлении документов в коллекцию '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to add documents batch: {e}")

        logger.info(
            f"Добавлено {len(valid_documents)} документов в коллекцию '{collection_name}'"
        )
        return len(valid_documents)

    async def search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Поиск документов по тексту с использованием embeddings."""
        collection = await self._get_collection(collection_name)

        if not query.strip():
            raise ChromaValidationError("Search query cannot be empty")

        try:
            results = await collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                where_document=where_document,
            )
        except Exception as e:
            logger.error(
                f"Ошибка при поиске документов в коллекции '{collection_name}': {e}"
            )
            raise ChromaSearchError(f"Failed to search documents: {e}")

        documents = []
        for i in range(len(results["ids"][0])):
            documents.append(
                {
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                    if "distances" in results
                    else None,
                }
            )

        logger.debug(
            f"Найдено {len(documents)} документов по запросу '{query}' в коллекции '{collection_name}'"
        )
        return documents

    async def get_by_id(
        self, document_id: str, collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """Получает документ по ID."""
        collection = await self._get_collection(collection_name)

        try:
            results = await collection.get(ids=[document_id])
        except Exception as e:
            logger.error(
                f"Ошибка при получении документа {document_id} из коллекции '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to get document {document_id}: {e}")

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "text": results["documents"][0],
                "metadata": results["metadatas"][0],
            }

        return None

    async def update(self, document: BaseDocument, collection_name: str) -> bool:
        """Обновляет существующий документ в ChromaDB."""
        collection = await self._get_collection(collection_name)

        document_id = document.get_document_id()
        text_content = document.get_text_content()

        if not text_content.strip():
            raise ChromaValidationError(
                f"Document {document_id} has empty text content"
            )

        try:
            await collection.update(
                ids=[document_id],
                documents=[text_content],
                metadatas=[document.to_metadata()],
            )
        except Exception as e:
            logger.error(
                f"Ошибка при обновлении документа {document_id} в коллекции '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to update document {document_id}: {e}")

        logger.debug(f"Документ {document_id} обновлен в коллекции '{collection_name}'")
        return True

    async def delete(self, document_id: str, collection_name: str) -> bool:
        """Удаляет документ из ChromaDB."""
        collection = await self._get_collection(collection_name)

        try:
            await collection.delete(ids=[document_id])
        except Exception as e:
            logger.error(
                f"Ошибка при удалении документа {document_id} из коллекции '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to delete document {document_id}: {e}")

        logger.debug(f"Документ {document_id} удален из коллекции '{collection_name}'")
        return True

    async def get_by_metadata(
        self, where: Dict[str, Any], collection_name: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получает документы по метаданным."""
        collection = await self._get_collection(collection_name)

        try:
            results = await collection.get(where=where, limit=limit)
        except Exception as e:
            logger.error(
                f"Ошибка при поиске документов по метаданным в коллекции '{collection_name}': {e}"
            )
            raise ChromaSearchError(f"Failed to search documents by metadata: {e}")

        documents = []
        for i in range(len(results["ids"])):
            documents.append(
                {
                    "id": results["ids"][i],
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                }
            )

        return documents

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Получает информацию о коллекции."""
        collection = await self._get_collection(collection_name)

        try:
            count = await collection.count()
        except Exception as e:
            logger.error(
                f"Ошибка при получении информации о коллекции '{collection_name}': {e}"
            )
            raise ChromaDocumentError(f"Failed to get collection info: {e}")

        return {
            "name": collection_name,
            "count": count,
            "embedding_model": self.embedding_model,
            "chroma_host": self.chroma_host,
            "chroma_port": self.chroma_port,
        }

    async def close(self):
        """Закрывает соединение с ChromaDB."""
        if self._client:
            self._client = None
            self._collections.clear()
            logger.info("Соединение с ChromaDB закрыто")
