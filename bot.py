import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from config import config
from database.db import engine, async_session, upgrade_schema
from database.models import Base
from database.queries import ensure_default_settings, get_setting
from handlers import admin, balance, orders, referral, start, tasks, topup, withdraw

# Setup logging
logging.basicConfig(level=logging.INFO)

class DbMiddleware(BaseMiddleware):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def __call__(self, handler, event, data):
        async with async_session() as session:
            data['db'] = session
            data['bot'] = self.bot
            return await handler(event, data)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await upgrade_schema()
    async with async_session() as session:
        await ensure_default_settings(session)
        stored_contact = await get_setting(session, "admin_contact", config.ADMIN_CONTACT or "")
        if stored_contact:
            config.ADMIN_CONTACT = stored_contact

async def main():
    # Create database tables
    await create_tables()

    # Initialize bot and dispatcher
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Add middleware
    dp.update.middleware(DbMiddleware(bot))

    # Include routers
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(orders.router)
    dp.include_router(referral.router)
    dp.include_router(topup.router)
    dp.include_router(balance.router)
    dp.include_router(withdraw.router)
    dp.include_router(admin.router)

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
