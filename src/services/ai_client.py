from typing import Protocol, TYPE_CHECKING
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

