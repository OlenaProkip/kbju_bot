from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import load_config
from .db import Database
from .handlers import build_router
from .ui import BOT_COMMANDS


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    db = Database(config.database_path)
    db.init()

    bot = Bot(token=config.bot_token)
    await bot.set_my_commands(BOT_COMMANDS)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(build_router(db))
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
