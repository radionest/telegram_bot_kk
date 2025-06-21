from typing import Protocol, TYPE_CHECKING, Optional
from models.analysis import (
    TopicAnalysisRequest,
    TopicAnalysisResult,
)

if TYPE_CHECKING:
    from src.services.message_history_storage import MessageHistoryStorage


class AiClient(Protocol):
    message_history_storage: "MessageHistoryStorage"
    
    def __init__(self, model_name: str) -> None: 
        ...

    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult: 
        ...
    
    async def generate_free_response(
        self, message: str, chat_id: int, topic_id: Optional[int] = None
    ) -> str:
        """Generate a free-form response to a message.
        
        Args:
            message: The user's message
            chat_id: The chat ID for context
            
        Returns:
            Generated response
        """
        ...

