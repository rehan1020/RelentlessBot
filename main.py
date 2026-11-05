import asyncio
import logging
import sys

from src.config import settings
from src.database.db import init_db
from src.services.scheduler import setup_scheduler
from src.bot import create_app, set_bot_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("relentless_bot")

async def main():
    logger.info("Initializing RelentlessBot...")
    
    if not settings.bot_token:
        logger.error("Error: BOT_TOKEN is missing! Please configure it in your .env file.")
        sys.exit(1)

    # 1. Initialize SQLite Database & Tables
    await init_db()
    logger.info(f"Database initialized at {settings.db_path}")

    # 2. Build Bot and Dispatcher
    bot, dp = await create_app()

    # 3. Setup commands menu in Telegram
    await set_bot_commands(bot)

    # 4. Start Background Scheduler
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info(f"Scheduler started (Timezone: {settings.timezone}, Quiet Hours: {settings.quiet_hours_start}-{settings.quiet_hours_end})")

    try:
        logger.info("Starting bot polling... Press Ctrl+C to stop.")
        # Delete any pending webhook updates and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Closing bot session...")
        await bot.session.close()
        logger.info("RelentlessBot stopped cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated.")
