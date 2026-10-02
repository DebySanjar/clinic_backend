"""
DentFlow Bot — Entry point (aiogram 3.x)

Ishga tushirish:
  Polling (local dev): python bot/main.py
  Webhook (production): Django view orqali /api/bot/webhook/
"""

import os
import sys
import asyncio
import logging

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.start import router as start_router
from bot.reminders import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot & dp instances (webhook uchun ham import qilinadi)
bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# Routerlarni ro'yxatdan o'tkazish
dp.include_router(start_router)


async def on_startup():
    """Bot ishga tushganda"""
    webhook_url = getattr(settings, 'WEBHOOK_URL', None)

    if webhook_url:
        # Production: webhook o'rnatish
        await bot.set_webhook(
            url=f"{webhook_url}/api/bot/webhook/",
            drop_pending_updates=True
        )
        logger.info(f"Webhook o'rnatildi: {webhook_url}/api/bot/webhook/")
    else:
        # Local dev: webhookni o'chirish
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Polling rejimida ishlamoqda...")

    # Bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot ishga tushdi: @{bot_info.username}")


async def on_shutdown():
    """Bot to'xtaganda"""
    logger.info("Bot to'xtatilmoqda...")
    await bot.session.close()


async def main():
    """Polling rejimida ishga tushirish (local dev)"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Reminder scheduler
    scheduler = setup_scheduler(bot)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()


if __name__ == '__main__':
    asyncio.run(main())
