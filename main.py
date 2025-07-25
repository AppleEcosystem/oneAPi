import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import Config
from database import Database
from handlers import router
from background_tasks import BackgroundTaskManager

async def main():
    """Main function to start the bot"""
    
    config = Config()
    db = Database()
    await db.init_db()
    
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(router)
    
    dp["db"] = db
    dp["config"] = config
    
    # Start background tasks
    task_manager = BackgroundTaskManager(db, config)
    await task_manager.start()
    
    try:
        await dp.start_polling(bot)
    finally:
        await task_manager.stop()
        await bot.session.close()
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
