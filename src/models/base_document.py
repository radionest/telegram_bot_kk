from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseDocument(ABC):
    """Базовый интерфейс для всех документов, сохраняемых в ChromaDB."""

    @abstractmethod
    def get_document_id(self) -> str:
        """Возвращает уникальный идентификатор документа."""
        pass

    @abstractmethod
    def get_text_content(self) -> str:
        """Возвращает текстовое содержимое для индексации."""
        pass

    @abstractmethod
    def to_metadata(self) -> Dict[str, Any]:
        """Преобразует документ в метаданные для ChromaDB."""
        pass
