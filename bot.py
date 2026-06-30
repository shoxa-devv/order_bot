import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import common, catalog, cart, checkout, admin

async def main():
    # Setup basic logging to standard output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("telegram_bot")

    if not BOT_TOKEN:
        logger.error("XATOLIK: BOT_TOKEN topilmadi! Iltimos, .env faylini to'g'irlang va qayta urining.")
        return

    # Initialize bot instance
    bot = Bot(token=BOT_TOKEN)
    
    # Initialize dispatcher with memory storage for FSM
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers in correct order
    # Registering admin handler first ensures admin commands are intercepted correctly
    dp.include_router(admin.router)
    dp.include_router(common.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)

    # Initialize SQLite database & apply seeds
    logger.info("Ma'lumotlar bazasi jadvallari yaratilmoqda...")
    await init_db()
    logger.info("Ma'lumotlar bazasi tayyor.")

    # Drop pending updates and start polling
    logger.info("Bot poller ishga tushirilmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    finally:
        # Properly close bot session when stopping
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
