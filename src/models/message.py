from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from models.base_document import BaseDocument


class StoredMessage(BaseModel, BaseDocument):
    """Модель сообщения для хранения в ChromaDB."""
    
    message_id: int
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    text: str
    chat_id: int
    chat_type: str  # private, group, supergroup, channel
    chat_title: Optional[str] = None
    timestamp: datetime
    reply_to_message_id: Optional[int] = None
    media_ids: List[str] = Field(default_factory=list)
    media_captions: List[str] = Field(default_factory=list)
    
    def to_metadata(self) -> dict:
        """Преобразует сообщение в метаданные для ChromaDB."""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "username": self.username or "",
            "first_name": self.first_name or "",
            "last_name": self.last_name or "",
            "chat_id": self.chat_id,
            "chat_type": self.chat_type,
            "chat_title": self.chat_title or "",
            "timestamp": self.timestamp.isoformat(),
            "reply_to_message_id": self.reply_to_message_id or 0,
            "media_count": len(self.media_ids),
            "has_media": len(self.media_ids) > 0
        }
    
    def get_document_id(self) -> str:
        """Генерирует уникальный ID документа для ChromaDB."""
        return f"{self.chat_id}_{self.message_id}"
    
    def get_full_text(self) -> str:
        """Возвращает полный текст для индексации, включая подписи к медиа."""
        parts = [self.text] if self.text else []
        parts.extend(self.media_captions)
        return " ".join(filter(None, parts))
    
    def get_text_content(self) -> str:
        """Реализация метода BaseDocument для получения текстового содержимого."""
        return self.get_full_text()
    
    @classmethod
    def from_aiogram_message(cls, message) -> "StoredMessage":
        """Создает StoredMessage из aiogram Message объекта."""
        media_ids = []
        media_captions = []
        
        # Извлечение информации о медиафайлах
        if message.photo:
            media_ids.append(message.photo[-1].file_id)
            if message.caption:
                media_captions.append(message.caption)
        elif message.video:
            media_ids.append(message.video.file_id)
            if message.caption:
                media_captions.append(message.caption)
        elif message.document:
            media_ids.append(message.document.file_id)
            if message.caption:
                media_captions.append(message.caption)
        elif message.audio:
            media_ids.append(message.audio.file_id)
            if message.caption:
                media_captions.append(message.caption)
        elif message.voice:
            media_ids.append(message.voice.file_id)
        
        return cls(
            message_id=message.message_id,
            user_id=message.from_user.id if message.from_user else 0,
            username=message.from_user.username if message.from_user else None,
            first_name=message.from_user.first_name if message.from_user else None,
            last_name=message.from_user.last_name if message.from_user else None,
            text=message.text or "",
            chat_id=message.chat.id,
            chat_type=message.chat.type,
            chat_title=message.chat.title,
            timestamp=message.date,
            reply_to_message_id=message.reply_to_message.message_id if message.reply_to_message else None,
            media_ids=media_ids,
            media_captions=media_captions
        )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }