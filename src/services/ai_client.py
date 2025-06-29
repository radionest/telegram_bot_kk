from typing import Protocol, TYPE_CHECKING, Optional
from models.analysis import (
    TopicAnalysisRequest,
    TopicAnalysisResult,
)

if TYPE_CHECKING:
    from services.message_history_storage import MessageHistoryStorage


class AiClient(Protocol):
    """Protocol defining the interface for AI clients.

    This protocol ensures consistent interface across different AI providers
    (Groq, Gemini, etc.) for message analysis and response generation.
    """

    message_history_storage: "MessageHistoryStorage"

    def __init__(self, model_name: str) -> None:
        """Initialize the AI client.

        Args:
            model_name: The name of the AI model to use
        """
        ...

    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult:
        """Analyze if a message complies with topic requirements.

        Args:
            request: The analysis request containing message and topic details

        Returns:
            Analysis result with compliance decision and confidence score
        """
        ...

    async def generate_free_response(
        self, message: str, chat_id: int, topic_id: Optional[int] = None
    ) -> str:
        """Generate a free-form response to a message.

        Args:
            message: The user's message
            chat_id: The chat ID for context
            topic_id: Optional topic ID for conversation context

        Returns:
            Generated response
        """
        ...
