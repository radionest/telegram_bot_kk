"""Base AI client with prompt generation logic."""

import json
from typing import Optional
from abc import ABC, abstractmethod

from models.analysis import TopicAnalysisRequest, TopicAnalysisResult
from models.message_history import MessageHistoryStorage
from utils.logger import logger
from exceptions import APIError


class BaseAiClient(ABC):
    """Base AI client with common prompt generation logic.

    This class contains all the business logic for generating prompts
    and processing responses, while delegating the actual API calls
    to provider implementations.
    """

    def __init__(
        self,
        message_history_storage: Optional[MessageHistoryStorage] = None,
        temperature: float = 0.7,
    ):
        """Initialize the base AI client.

        Args:
            message_history_storage: Optional storage for conversation history
            temperature: Default temperature for text generation
        """
        self.message_history_storage = message_history_storage
        self.temperature = temperature

    @abstractmethod
    async def _generate_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using the provider's API.

        This method must be implemented by provider-specific subclasses.

        Args:
            prompt: The input prompt
            temperature: Override default temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        pass

    def _clean_json_from_response(self, response_text: str) -> str:
        """Parse JSON from response, removing markdown formatting if present.

        Args:
            response_text: Raw response text from AI API

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

    async def _build_message_history_context(
        self, request: TopicAnalysisRequest
    ) -> str:
        """Build context from message history.

        Args:
            request: Topic analysis request

        Returns:
            Formatted message history as string
        """
        if not self.message_history_storage:
            return ""

        context_parts = []

        # Get message history from topic
        history_messages = await self.message_history_storage.get_topic_messages(
            chat_id=request.chat_id, topic_id=request.topic_id, limit=10
        )

        if history_messages:
            context_parts.append("ИСТОРИЯ ПОСЛЕДНИХ СООБЩЕНИЙ В ТЕМЕ:")
            for msg in history_messages:
                if (
                    msg.message_id != request.message_id
                ):  # Don't include current message
                    username = (
                        msg.from_user.username if msg.from_user else "Неизвестный"
                    )
                    text = msg.text or "[медиа]"
                    context_parts.append(f"- @{username}: {text}")

        # If this is a reply, add the original message
        if request.reply_to_message_id:
            # Find original message in history
            for msg in history_messages:
                if msg.message_id == request.reply_to_message_id:
                    username = (
                        msg.from_user.username if msg.from_user else "Неизвестный"
                    )
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

        # Get message history context
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
            response_text = await self._generate_text(prompt, temperature=0.3)

            if not response_text:
                logger.error("Empty response from AI API")
                raise APIError("Empty response from AI API")

            # Parse JSON response
            cleaned_response = self._clean_json_from_response(response_text)

            parsed_response: dict = json.loads(cleaned_response)
            return TopicAnalysisResult(
                is_appropriate=parsed_response.get("is_appropriate", True),
                suggested_topic=parsed_response.get("suggested_topic"),
                confidence=float(parsed_response.get("confidence", 0.5)),
                reason=parsed_response.get("reason", "Анализ завершен"),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(
                f"Raw response: {response_text if 'response_text' in locals() else 'N/A'}"
            )

            # Fallback: assume message is appropriate if parsing fails
            return TopicAnalysisResult(
                is_appropriate=True,
                confidence=0.0,
                reason="Ошибка анализа - принято как подходящее",
            )
        except Exception as e:
            logger.error(f"Error in topic compliance analysis: {e}")
            raise

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
        try:
            # Get message history for context
            history_messages = []
            if self.message_history_storage:
                history_messages = (
                    await self.message_history_storage.get_topic_messages(
                        chat_id=chat_id, topic_id=topic_id, limit=10
                    )
                )

            # Build context from history
            context_parts = []
            for msg in reversed(history_messages):
                username = msg.from_user.username if msg.from_user else "Неизвестный"
                text = msg.text or "[медиа]"
                context_parts.append(f"@{username}: {text}")

            context = (
                "\n".join(context_parts)
                if context_parts
                else "Нет предыдущих сообщений"
            )

            prompt = f"""
            Ты - дружелюбный и полезный ассистент в Telegram чате. 
            Обычная твоя задача модерировать сообщения в темах. 
            Отвечай кратко, по существу и в дружелюбном тоне. 
            Но на грубое обращение отвечай грубостью.    
          
            КОНТЕКСТ ЧАТА:
            {context}
       
            ТЕКУЩЕЕ СООБЩЕНИЕ: {message}
        
            Дай краткий и полезный ответ на это сообщение.
            """

            response = await self._generate_text(
                prompt, temperature=self.temperature, max_tokens=500
            )

            if response:
                return response.strip()
            else:
                return "Извините, не могу сформулировать ответ."

        except Exception as e:
            logger.error(f"Error generating free response: {e}")
            return "Извините, произошла ошибка при генерации ответа."
