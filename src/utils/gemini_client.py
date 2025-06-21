"""Gemini API client for message analysis."""

import json
from typing import TYPE_CHECKING, List, Optional

from google import genai
from google.genai import types

from config.settings import settings
from models.analysis import (
    TopicAnalysisRequest,
    TopicAnalysisResult,
)
from utils.logger import logger
from services.ai_client import AiClient
from exceptions import APIError

if TYPE_CHECKING:
    from src.services.message_history_storage import MessageHistoryStorage

# Client initialization moved to __init__ method


class GeminiClient(AiClient):
    """Client for interacting with Google's Gemini API."""

    def __init__(self, model_name: str = "gemini-2.0-flash-001", message_history_storage: Optional["MessageHistoryStorage"] = None) -> None:
        """Initialize Gemini client.

        Args:
            model_name: The Gemini model to use
            message_history_storage: Storage for message history
        """
        # Configure proxy if provided
        if settings.HTTP_PROXY or settings.HTTPS_PROXY:
            proxy_url = settings.HTTPS_PROXY or settings.HTTP_PROXY
            http_options = types.HttpOptions(
                client_args={'proxy': proxy_url},
                async_client_args={'proxy': proxy_url}
            )
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)
            logger.info(f"Initialized Gemini client with proxy: {proxy_url}")
        else:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info("Initialized Gemini client without proxy")
            
        self.model_name = model_name
        self.message_history_storage = message_history_storage
        logger.info(f"Using model: {model_name}")

    def _clean_json_from_response(self, response_text: str) -> str:
        """Parse JSON from response, removing markdown formatting if present.

        Args:
            response_text: Raw response text from Gemini API

        Returns:
            Parsed JSON as dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        # Clean the response text - remove markdown formatting if present
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        return response_text.strip()
    
    async def _build_message_history_context(self, request: TopicAnalysisRequest) -> str:
        """Build context from message history.
        
        Args:
            request: Topic analysis request
            
        Returns:
            Formatted message history as string
        """
        if not self.message_history_storage:
            return ""
        
        context_parts = []
        
        # Получаем историю сообщений из темы
        history_messages = await self.message_history_storage.get_topic_messages(
            chat_id=request.chat_id,
            topic_id=request.topic_id,
            limit=10
        )
        
        if history_messages:
            context_parts.append("ИСТОРИЯ ПОСЛЕДНИХ СООБЩЕНИЙ В ТЕМЕ:")
            for msg in history_messages:
                if msg.message_id != request.message_id:  # Не включаем текущее сообщение
                    username = msg.from_user.username if msg.from_user else "Неизвестный"
                    text = msg.text or "[медиа]"
                    context_parts.append(f"- @{username}: {text}")
        
        # Если это ответ на сообщение, добавляем оригинальное сообщение
        if request.reply_to_message_id:
            # Ищем оригинальное сообщение в истории
            for msg in history_messages:
                if msg.message_id == request.reply_to_message_id:
                    username = msg.from_user.username if msg.from_user else "Неизвестный"
                    text = msg.text or "[медиа]"
                    context_parts.insert(0, f"ОТВЕТ НА СООБЩЕНИЕ: @{username}: {text}")
                    break
        
        return "\n".join(context_parts) if context_parts else ""

    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult:
        """Analyze if a message is appropriate for its topic.

        Args:
            request: Topic analysis request with message and topic details

        Returns:
            Topic analysis result with compliance assessment

        Raises:
            Exception: If API request fails
        """
        # Build available topics description
        available_topics_info = "\n".join(
            [
                f"- {topic.name}: {topic.description}"
                for topic in request.available_topics
            ]
        )

        # Получаем контекст истории сообщений
        message_context = await self._build_message_history_context(request)
        
        prompt = f"""
        Проанализируй, подходит ли данное сообщение для текущей темы форума.
        ТЕКУЩАЯ ТЕМА: {request.current_topic}
        ОПИСАНИЕ ТЕМЫ: {request.current_topic_description}

        ДОСТУПНЫЕ ТЕМЫ ФОРУМА:
        {available_topics_info}
        
        {message_context}

        СООБЩЕНИЕ ДЛЯ АНАЛИЗА: {request.message_text}

        Ответь в формате JSON:
        {{
            "is_appropriate": true/false,
            "suggested_topic": "название_темы" или null,
            "confidence": число от 0.0 до 1.0,
            "reason": "краткое объяснение"
        }}

        Правила анализа:
        1. Сообщение подходит теме, если его содержание соответствует описанию темы
        2. Учитывай контекст беседы и историю сообщений при анализе
        3. Если это ответ на другое сообщение, учитывай содержание оригинального сообщения
        4. Если сообщение не подходит, предложи наиболее подходящую тему из доступных
        5. Confidence показывает уверенность в анализе (0.0 - не уверен, 1.0 - полностью уверен)
        6. В reason кратко объясни почему сообщение подходит или не подходит теме
        7. Не надо вставлять текст самого сообщения в reason
        8. Не используй двойные кавычки внутри reason
        """

        logger.debug(
            f"Analyzing topic compliance for message in topic '{request.current_topic}'"
        )
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt
        )

        if not response.text:
            logger.error(
                f"Empty response from Gemini API for promt: \n {prompt} \n {'-' * 20}"
            )
            raise APIError("Empty response from Gemini API", api_name="Gemini")

        # Parse JSON response
        cleaned_response = self._clean_json_from_response(response.text)

        try:
            parsed_response: dict = json.loads(cleaned_response)
            return TopicAnalysisResult(
                is_appropriate=parsed_response.get("is_appropriate", True),
                suggested_topic=parsed_response.get("suggested_topic"),
                confidence=float(parsed_response.get("confidence", 0.5)),
                reason=parsed_response.get("reason", "Анализ завершен"),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Raw response: {response.text}")

            # Fallback: assume message is appropriate if parsing fails
            return TopicAnalysisResult(
                is_appropriate=True,
                confidence=0.0,
                reason="Ошибка анализа - принято как подходящее",
            )
