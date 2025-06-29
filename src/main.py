"""Main entry point for the Telegram bot."""

import asyncio
from typing import NoReturn

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from exceptions import ConfigError
from middlewares.message_history_middleware import MessageHistoryMiddleware
from middlewares.topic_update_middleware import TopicUpdateMiddleware
from routers.message_handlers import router as message_router
from routers.admin import router as admin_router
from services.chat_manager import ChatManager
from services.chroma_crud import ChromaCRUD
from models.message import StoredMessage
from services.chroma_message_storage import ChromaMessageHistoryStorage
from services.memory_topic_storage import MemoryTopicStorage
from services.response_manager import ResponseManager
from services.group_tracker import GroupTracker
from utils.litellm_client import LiteLLMClient, RouterConfig
from utils.logger import logger


async def main() -> None:
    """Initialize and run the bot.
    
    Raises:
        Exception: If bot initialization fails
    """
    logger.info("Initializing bot...")

    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    
    # Initialize ChromaDB
    chroma_crud = ChromaCRUD(
        chroma_host=settings.CHROMA_HOST,
        chroma_port=settings.CHROMA_PORT,
        embedding_model=settings.CHROMA_EMBEDDING_MODEL
    )
    
    message_history_storage = ChromaMessageHistoryStorage(chroma_crud,
                                                          collection_name='telegram_messages')
    topic_storage = MemoryTopicStorage()
    group_tracker = GroupTracker()
    
    # Initialize LiteLLM client
    config_path = getattr(settings, 'LITELLM_CONFIG_PATH', 'litellm_models.yaml')
    router_strategy = getattr(settings, 'LITELLM_ROUTER_STRATEGY', 'priority')
    
    ai_client = LiteLLMClient(
        config_path=config_path,
        router_config=RouterConfig(strategy=router_strategy),
        message_history_storage=message_history_storage
    )
    logger.info(f"Using LiteLLM with {len(ai_client.models)} models and {router_strategy} routing")
    
    chat_manager = ChatManager(
        bot,
        ai_manager=ai_client,
        group_tracker=group_tracker
    )
    
    # Initialize bot info in chat manager
    await chat_manager.initialize_bot_info()
    
    dp = Dispatcher(
        storage=storage,
        chat_manager=chat_manager,
        response_manager=ResponseManager(bot, chat_manager),
        group_tracker=group_tracker,
        message_history_storage=message_history_storage,
        topic_storage=topic_storage,
    )

    # Initialize managers
    logger.info("Initializing chat and response managers...")

    # Register middleware
    dp.message.middleware(TopicUpdateMiddleware())
    dp.message.middleware(MessageHistoryMiddleware())

    # Include routers
    dp.include_router(admin_router)  # Admin commands should be registered first
    dp.include_router(message_router)

    # Delete webhook to use polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.success("Bot started successfully!")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error while running bot: {e}")
        raise
    finally:
        await bot.session.close()
        logger.warning("Bot stopped")


def run() -> NoReturn:
    """Run the bot with proper error handling.
    
    Raises:
        SystemExit: On critical errors or configuration issues
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except ConfigError as e:
        logger.critical(f"Configuration error: {e}")
        exit(1)

    except Exception as e:
        logger.critical(f"Critical error: {e}")
        exit(1)
    exit(0)


if __name__ == "__main__":
    run()
