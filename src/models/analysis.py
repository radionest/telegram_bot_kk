"""Models for message analysis."""

from enum import Enum
from typing import Optional, Protocol, Iterable

from pydantic import BaseModel, Field


class ResponseType(Enum):
    """Types of bot responses."""

    REACTION = "reaction"
    MESSAGE = "message"


class AnalysisRequest(BaseModel):
    """Request for message analysis."""

    message_text: str
    chat_id: int
    user_id: int
    username: Optional[str] = None


class AnalysisResult(BaseModel):
    """Result of message analysis."""

    text: str
    response_type: ResponseType
    confidence: Optional[float] = None


class Topic(Protocol):
    name: str
    description: str


class TopicAnalysisRequest(BaseModel):
    """Request for topic compliance analysis."""

    message_text: str
    current_topic: str
    current_topic_description: str
    available_topics: Iterable[Topic]
    chat_id: int
    user_id: int
    message_id: int
    topic_id: Optional[int] = None  # ID темы для получения истории
    reply_to_message_id: Optional[int] = None  # ID сообщения на которое отвечаем


class TopicAnalysisResult(BaseModel):
    """Result of topic compliance analysis."""

    is_appropriate: bool
    suggested_topic: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
