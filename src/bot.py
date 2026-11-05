import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from src.config import settings
from src.database.db import init_db
from src.middlewares.auth import WhitelistMiddleware
from src.handlers import start, tasks, callbacks
from src.services.scheduler import setup_scheduler

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """Sets standard menu commands in the Telegram client UI."""
    commands = [
        BotCommand(command="tasks", description="View active tasks & progress"),
        BotCommand(command="clear", description="Clear or reset tasks"),
        BotCommand(command="help", description="How to use RelentlessBot"),
        BotCommand(command="start", description="Welcome & overview"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

async def create_app():
    """Initializes bot, dispatcher, middlewares, and routes."""
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN is not set in environment or .env file.")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Register Middlewares
    whitelist = WhitelistMiddleware()
    dp.message.middleware(whitelist)
    dp.callback_query.middleware(whitelist)

    # Register Routers
    dp.include_router(start.router)
    dp.include_router(callbacks.router)
    dp.include_router(tasks.router)

    return bot, dp
