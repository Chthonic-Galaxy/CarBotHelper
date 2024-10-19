import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.scene import SceneRegistry
from aiogram.fsm.storage.memory import SimpleEventIsolation

from bumblebeereminderbot.config import TOKEN
from bumblebeereminderbot.telegram.handlers.user_private import user_private, Menu, Profile, Notes, Purchase, Analisis, Reminders
from bumblebeereminderbot.telegram.common.bot_cmds_list import private
from bumblebeereminderbot.telegram.middlewares.scheduler import CounterMiddleware

from bumblebeereminderbot.database.models import async_main

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
scene_registry.add(Menu, Profile, Notes, Purchase, Analisis, Reminders)

# Создаем хранилище задач SQLAlchemy (важно для сохранения задач между перезапусками)
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite') # Или URL вашей базы данных
}
# Создаем планировщик задач *вне* обработчиков, один раз
scheduler = AsyncIOScheduler(jobstores=jobstores)



async def on_startup(bot: Bot):
    """Запускает планировщик задач при старте бота."""
    scheduler.start()
    print("APScheduler started")



async def on_shutdown(bot: Bot):
    """Останавливает планировщик задач при выключении бота."""
    scheduler.shutdown()
    print("APScheduler stopped")


async def main() -> None:
    """
    Основная функция для запуска бота и взаимодействия с базой данных.
    """
    try:
        # Запуск и создание базы данных
        await async_main()
        # Регистрируем функцию on_startup, которая будет вызвана при запуске бота
        dp.startup.register(on_startup) 
        # Регистрируем функцию on_shutdown, которая будет вызвана при остановке бота
        dp.shutdown.register(on_shutdown)
        # Добавление middleware для диспетчера с использованием планировщика
        dp.update.middleware(CounterMiddleware(scheduler=scheduler))
        # Установка команд бота для всех приватных чатов
        await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
        # Запуск поллинга (прослушивания обновлений)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.exceptions.CancelledError as e:
        print(e)

if __name__ == "__main__":
    asyncio.run(main())