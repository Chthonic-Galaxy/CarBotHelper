import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.scene import SceneRegistry
from aiogram.fsm.storage.memory import SimpleEventIsolation

from config import TOKEN
from telegram.handlers.user_private import user_private, Menu, Profile, Notes, Purchase
from telegram.common.bot_cmds_list import private

from database.models import async_main

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(filename="log.log", filemode="w", level=logging.DEBUG)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(events_isolation=SimpleEventIsolation())

# Подключение роутеров
dp.include_router(user_private)

# Регистрация сцен
scene_registry = SceneRegistry(dp)
scene_registry.add(Menu, Profile, Notes, Purchase)

async def main() -> None:
    try:
        # Запуск и создание базы данных
        await async_main()
        # Установка команд бота для всех приватных чатов
        await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
        # Запуск поллинга (прослушивания обновлений)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.exceptions.CancelledError as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
