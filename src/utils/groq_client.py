"""Groq API client for message analysis."""

import json
from typing import TYPE_CHECKING, Optional

from groq import Groq

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


class GroqClient(AiClient):
    """Client for interacting with Groq's API."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile", message_history_storage: Optional["MessageHistoryStorage"] = None) -> None:
        """Initialize Groq client.

        Args:
            model_name: The Groq model to use
            message_history_storage: Storage for message history
        """
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model_name = model_name
        self.message_history_storage = message_history_storage
        logger.info(f"Initialized Groq client with model: {model_name}")

    def _clean_json_from_response(self, response_text: str) -> str:
        """Parse JSON from response, removing markdown formatting if present.

        Args:
            response_text: Raw response text from Groq API

        Returns:
            Cleaned JSON string

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
            APIError: If API request fails
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
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - AI ассистент для анализа соответствия сообщений темам форума. Отвечай только в формате JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            
            if not response_text:
                logger.error(
                    f"Empty response from Groq API for prompt: \n {prompt} \n {'-' * 20}"
                )
                raise APIError("Empty response from Groq API", api_name="Groq")

            # Parse JSON response
            cleaned_response = self._clean_json_from_response(response_text)

            try:
                parsed_response: dict = json.loads(cleaned_response)
                return TopicAnalysisResult(
                    is_appropriate=parsed_response.get("is_appropriate", True),
                    suggested_topic=parsed_response.get("suggested_topic"),
                    confidence=float(parsed_response.get("confidence", 0.5)),
                    reason=parsed_response.get("reason", "Анализ завершен"),
                )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse Groq response: {e}")
                logger.error(f"Raw response: {response_text}")

                # Fallback: assume message is appropriate if parsing fails
                return TopicAnalysisResult(
                    is_appropriate=True,
                    confidence=0.0,
                    reason="Ошибка анализа - принято как подходящее",
                )
                
        except Exception as e:
            logger.error(f"Groq API request failed: {e}")
            raise APIError(f"Groq API request failed: {str(e)}", api_name="Groq")