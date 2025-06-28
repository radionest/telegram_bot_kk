"""LiteLLM-based universal AI client with multi-model support and intelligent routing."""

import random
from typing import Optional, Dict, Any, List, Union
import yaml
import json
from pathlib import Path

import litellm
from litellm import acompletion
from loguru import logger
from pydantic import BaseModel, Field

from models.analysis import (
    TopicAnalysisRequest,
    TopicAnalysisResult,
)
from services.message_history_storage import MessageHistoryStorage
from services.game_knowledge_service import GameKnowledgeService
from exceptions import APIError


class ModelConfig(BaseModel):
    """Configuration for a single AI model."""

    name: str
    provider: str
    api_key: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30
    max_retries: int = 3
    priority: int = 1
    tags: List[str] = Field(default_factory=list)
    extra_params: Dict[str, Any] = Field(default_factory=dict)
    proxy: Optional[str] = None  # HTTP/HTTPS/SOCKS5 proxy URL

    @property
    def model_id(self) -> str:
        """Get LiteLLM model identifier."""
        if self.provider in ["openai", "anthropic", "cohere"]:
            return self.name
        return f"{self.provider}/{self.name}"


class RouterConfig(BaseModel):
    """Configuration for request routing."""

    strategy: str = "round_robin"  # round_robin, priority, random, load_balance
    fallback_enabled: bool = True
    max_fallback_attempts: int = 3
    health_check_interval: int = 300  # seconds
    model_selection_rules: Dict[str, Any] = Field(default_factory=dict)


class LiteLLMClient:
    """Universal AI client using LiteLLM for multi-provider support."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        models: Optional[List[ModelConfig]] = None,
        router_config: Optional[RouterConfig] = None,
        message_history_storage: Optional[MessageHistoryStorage] = None,
        game_knowledge_service: Optional[GameKnowledgeService] = None,
    ):
        """Initialize LiteLLM client.

        Args:
            config_path: Path to YAML configuration file
            models: List of model configurations (if not using config file)
            router_config: Router configuration
            message_history_storage: Message history storage instance
        """
        self.message_history_storage = message_history_storage
        self.game_knowledge_service = game_knowledge_service
        self.router_config = router_config or RouterConfig()

        # Load models from config or use provided list
        if config_path:
            self.models = self._load_models_from_config(config_path)
        elif models:
            self.models = models
        else:
            raise ValueError("Either config_path or models must be provided")

        # Initialize model states
        self.model_states: Dict[str, Dict[str, Any]] = {}
        self._current_model_index = 0

        # Configure LiteLLM
        litellm.drop_params = True
        litellm.set_verbose = False

        # Set up API keys
        self._setup_api_keys()

        # Initialize model health states
        for model in self.models:
            self.model_states[model.model_id] = {
                "available": True,
                "last_error": None,
                "error_count": 0,
                "last_used": None,
                "total_requests": 0,
                "failed_requests": 0,
            }

        logger.info(f"Initialized LiteLLM client with {len(self.models)} models")

    def _load_models_from_config(
        self, config_path: Union[str, Path]
    ) -> List[ModelConfig]:
        """Load model configurations from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        models = []
        providers = {p["name"]: p["api_key"] for p in config.get("providers", [])}

        for model_config in config.get("models", []):
            provider = model_config["provider"]
            api_key = model_config.get("api_key", providers.get(provider))

            if not api_key:
                logger.warning(
                    f"No API key found for {provider}, skipping model {model_config.get('model_name')}"
                )
                continue

            models.append(
                ModelConfig(
                    name=model_config["model_name"],
                    provider=provider,
                    api_key=api_key,
                    temperature=model_config.get("temperature", 0.7),
                    max_tokens=model_config.get("max_tokens"),
                    timeout=model_config.get("timeout", 30),
                    max_retries=model_config.get("max_retries", 3),
                    priority=model_config.get("priority", 1),
                    tags=model_config.get("tags", []),
                    extra_params=model_config.get("extra_params", {}),
                    proxy=model_config.get("proxy"),
                )
            )

        return models

    def _setup_api_keys(self):
        """Set up API keys for all providers."""
        for model in self.models:
            if model.provider == "gemini":
                litellm.vertex_ai_api_key = model.api_key
            elif model.provider == "groq":
                litellm.groq_api_key = model.api_key
            elif model.provider == "openai":
                litellm.openai_api_key = model.api_key
            elif model.provider == "anthropic":
                litellm.anthropic_api_key = model.api_key

    def _select_model(self, tags: Optional[List[str]] = None) -> Optional[ModelConfig]:
        """Select a model based on routing strategy and availability."""
        available_models = [
            m for m in self.models if self.model_states[m.model_id]["available"]
        ]

        if not available_models:
            logger.error("No available models")
            return None

        # Filter by tags if provided
        if tags:
            tagged_models = [
                m for m in available_models if any(tag in m.tags for tag in tags)
            ]
            if tagged_models:
                available_models = tagged_models

        # Apply routing strategy
        if self.router_config.strategy == "round_robin":
            model = available_models[self._current_model_index % len(available_models)]
            self._current_model_index += 1
        elif self.router_config.strategy == "priority":
            model = max(available_models, key=lambda m: m.priority)
        elif self.router_config.strategy == "random":
            model = random.choice(available_models)
        elif self.router_config.strategy == "load_balance":
            # Select model with lowest error rate
            model = min(
                available_models,
                key=lambda m: (self.model_states[m.model_id]["failed_requests"] + 1)
                / max(1, self.model_states[m.model_id]["total_requests"]),
            )
        else:
            model = available_models[0]

        return model

    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from markdown formatting.
        
        Args:
            response: Raw response that may contain markdown formatting
            
        Returns:
            Cleaned JSON string
        """
        response = response.strip()
        
        # Check if response is wrapped in markdown code blocks
        if response.startswith("```"):
            # Remove opening markdown
            if response.startswith("```json"):
                response = response[7:]  # Remove ```json
            elif response.startswith("```"):
                response = response[3:]  # Remove ```
            
            # Remove closing markdown
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
        
        return response

    async def _make_request(
        self, messages: List[Dict[str, str]], model: ModelConfig, **kwargs
    ) -> str:
        """Make a request to a specific model."""
        state = self.model_states[model.model_id]
        state["total_requests"] += 1

        try:
            # Prepare request parameters
            params = {
                "model": model.model_id,
                "messages": messages,
                "temperature": model.temperature,
                "timeout": model.timeout,
                **model.extra_params,
                **kwargs,
            }

            if model.max_tokens:
                params["max_tokens"] = model.max_tokens

            # Set proxy if configured
            if model.proxy:
                import os

                # Store original proxy settings
                original_proxies = {
                    "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
                    "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
                    "http_proxy": os.environ.get("http_proxy"),
                    "https_proxy": os.environ.get("https_proxy"),
                }
                # Set proxy for this request
                os.environ["HTTP_PROXY"] = model.proxy
                os.environ["HTTPS_PROXY"] = model.proxy
                os.environ["http_proxy"] = model.proxy
                os.environ["https_proxy"] = model.proxy

            try:
                # Make async request
                response = await acompletion(**params)
            finally:
                # Restore original proxy settings if proxy was used
                if model.proxy:
                    for key, value in original_proxies.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value

            # Update state
            state["error_count"] = 0
            state["last_error"] = None

            return response.choices[0].message.content

        except Exception as e:
            state["failed_requests"] += 1
            state["error_count"] += 1
            state["last_error"] = str(e)

            # Mark model as unavailable after multiple failures
            if state["error_count"] >= model.max_retries:
                state["available"] = False
                logger.warning(
                    f"Model {model.model_id} marked as unavailable after {model.max_retries} failures"
                )

            raise APIError(f"Request to {model.model_id} failed: {e}")

    async def _request_with_fallback(
        self, messages: List[Dict[str, str]], tags: Optional[List[str]] = None, **kwargs
    ) -> str:
        """Make request with automatic fallback to other models."""
        attempted_models = []
        last_error = None

        for attempt in range(self.router_config.max_fallback_attempts):
            model = self._select_model(tags)

            if not model or model in attempted_models:
                continue

            attempted_models.append(model)
            logger.debug(
                f"Attempting request with {model.model_id} (attempt {attempt + 1})"
            )

            try:
                return await self._make_request(messages, model, **kwargs)
            except APIError as e:
                last_error = e
                logger.warning(f"Request failed with {model.model_id}: {e}")

                if not self.router_config.fallback_enabled:
                    raise

        raise APIError(f"All models failed. Last error: {last_error}")

    async def analyze_topic_compliance(
        self, request: TopicAnalysisRequest
    ) -> TopicAnalysisResult:
        """Analyze if a message complies with topic requirements."""
        # Build available topics description
        available_topics_info = "\n".join(
            [
                f"- {topic.name}: {topic.description}"
                for topic in request.available_topics
            ]
            if hasattr(request, "available_topics") and request.available_topics
            else []
        )

        # Build message history context
        message_context = ""
        if self.message_history_storage and request.chat_id:
            history = await self.message_history_storage.get_recent_messages(
                request.chat_id, limit=10
            )
            if history:
                context_parts = []
                for msg in reversed(history[:-1]):  # Exclude current message
                    username = msg.from_user.username or "Неизвестный"
                    text = msg.text or "[медиа]"
                    context_parts.append(f"@{username}: {text}")
                if context_parts:
                    message_context = f"\n\nКОНТЕКСТ ПРЕДЫДУЩИХ СООБЩЕНИЙ:\n{chr(10).join(context_parts)}"
        
        # Get game context if available
        game_context = ""
        if self.game_knowledge_service:
            # Extract potential game-related tags from message
            tags = self._extract_game_tags(request.message_text)
            game_context = await self.game_knowledge_service.get_game_context(
                topic=request.message_text,
                tags=tags,
                message_context=message_context,
                limit=3
            )
            if game_context:
                game_context = f"\n\n{game_context}"

        prompt = f"""
        Проанализируй, подходит ли данное сообщение для текущей темы форума.
        ТЕКУЩАЯ ТЕМА: {request.current_topic}
        ОПИСАНИЕ ТЕМЫ: {request.current_topic_description}

        {"ДОСТУПНЫЕ ТЕМЫ ФОРУМА:\n" + available_topics_info if available_topics_info else ""}
        
        {message_context}
        {game_context}

        СООБЩЕНИЕ ДЛЯ АНАЛИЗА: {request.message_text}

        Ответь в формате JSON:
        {{
            "is_appropriate": true/false,
            "suggested_topic": "название_темы" или null,
            "confidence": число от 0.0 до 1.0
        }}

        Правила анализа:
        1. Сообщение подходит теме, если его содержание соответствует описанию темы
        2. Учитывай контекст беседы и историю сообщений при анализе
        3. Если это ответ на другое сообщение, учитывай содержание оригинального сообщения
        4. Если сообщение не подходит, предложи наиболее подходящую тему из доступных
        5. Confidence показывает уверенность в анализе (0.0 - не уверен, 1.0 - полностью уверен)
        """

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self._request_with_fallback(
                messages, tags=["classification"]
            )

            # Parse response
            cleaned_response = self._clean_json_response(response)
            result = json.loads(cleaned_response)

            # Map is_appropriate to is_compliant for compatibility
            is_compliant = result.get(
                "is_appropriate", result.get("is_compliant", False)
            )

            return TopicAnalysisResult(
                is_appropriate=is_compliant,
                confidence=result.get("confidence", 0.0),
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return TopicAnalysisResult(
                is_appropriate=False,
                confidence=0.0,
            )

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
        # Get message history for context
        context = "Нет предыдущих сообщений"
        if self.message_history_storage:
            history = await self.message_history_storage.get_recent_messages(
                chat_id, limit=10
            )
            if history:
                context_parts = []
                for msg in reversed(history[:-1]):  # Exclude current message
                    username = msg.from_user.username or "Неизвестный"
                    text = msg.text or "[медиа]"
                    context_parts.append(f"@{username}: {text}")
                if context_parts:
                    context = "\n".join(context_parts)

        # Get game context for response
        game_context = ""
        if self.game_knowledge_service:
            tags = self._extract_game_tags(message)
            game_context = await self.game_knowledge_service.get_game_context(
                topic=message,
                tags=tags,
                message_context=context,
                limit=5
            )
            if game_context:
                game_context = f"\n\n{game_context}"
        
        prompt = f"""
        Ты - дружелюбный и полезный ассистент в Telegram чате клана War Legends. 
        Обычная твоя задача модерировать сообщения в темах. 
        Отвечай кратко, по существу и в дружелюбном тоне. 
        Но на грубое обращение отвечай грубостью.
        
        КОНТЕКСТ ЧАТА:
        {context}
        {game_context}
      
        ТЕКУЩЕЕ СООБЩЕНИЕ: {message}
    
        Дай краткий и полезный ответ на это сообщение, используя знания об игре когда это уместно.
        """

        messages = [{"role": "user", "content": prompt}]

        return await self._request_with_fallback(
            messages, tags=["conversation", "chat"]
        )

    async def health_check(self):
        """Check health of all models and re-enable recovered ones."""
        for model in self.models:
            state = self.model_states[model.model_id]

            # Skip if recently checked and available
            if state["available"]:
                continue

            # Try to re-enable model
            try:
                logger.info(f"Health checking {model.model_id}")
                await self._make_request(
                    [{"role": "user", "content": "Hi"}], model, max_tokens=10
                )
                state["available"] = True
                state["error_count"] = 0
                logger.info(f"Model {model.model_id} is now available")
            except Exception as e:
                logger.debug(f"Model {model.model_id} still unavailable: {e}")

    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics for all models."""
        stats = {}
        for model in self.models:
            state = self.model_states[model.model_id]
            stats[model.model_id] = {
                "provider": model.provider,
                "available": state["available"],
                "total_requests": state["total_requests"],
                "failed_requests": state["failed_requests"],
                "success_rate": (
                    (state["total_requests"] - state["failed_requests"])
                    / max(1, state["total_requests"])
                ),
                "last_error": state["last_error"],
            }
        return stats
    
    def _extract_game_tags(self, text: str) -> List[str]:
        """Extract potential game-related tags from text."""
        # Common game-related keywords
        game_keywords = {
            "юнит", "юниты", "unit", "units",
            "здание", "здания", "building", "buildings",
            "стратегия", "стратегии", "strategy", "strategies",
            "атака", "атаковать", "attack", "attacking",
            "защита", "защищать", "defense", "defending",
            "раш", "rush", "бум", "boom",
            "мечник", "лучник", "кавалерия", "копейщик", "катапульта", "рыцарь",
            "swordsman", "archer", "cavalry", "spearman", "catapult", "knight",
            "казармы", "конюшня", "мастерская",
            "barracks", "stable", "workshop",
            "ресурсы", "золото", "дерево", "еда", "камень",
            "resources", "gold", "wood", "food", "stone",
            "экономика", "economy",
            "бой", "сражение", "battle", "combat",
            "counter", "контр", "против",
        }
        
        text_lower = text.lower()
        found_tags = []
        
        for keyword in game_keywords:
            if keyword in text_lower:
                found_tags.append(keyword)
        
        return found_tags
