from typing import Callable, Any, Dict, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram.types import TelegramObject
from aiogram import BaseMiddleware, Bot


class CounterMiddleware(BaseMiddleware):
    """
    Middleware для интеграции APScheduler в обработчики Aiogram.
    Добавляет планировщик задач в данные, доступные для обработчиков.
    """
    
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        """
        Инициализация middleware с переданным планировщиком задач.

        :param scheduler: Экземпляр AsyncIOScheduler для планирования задач.
        """
        self.scheduler = scheduler

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Метод, вызываемый при каждом событии (сообщении) бота.
        Добавляет планировщик задач в данные, передаваемые обработчику.

        :param handler: Функция обработчика, которую необходимо вызвать.
        :param event: Объект события Telegram (например, Message).
        :param data: Словарь данных, передаваемых обработчику.
        :return: Результат выполнения обработчика.
        """
        # Добавление планировщика задач в словарь данных
        data["apscheduler"] = self.scheduler
        # Вызов следующего обработчика в цепочке с обновленными данными
        return await handler(event, data)


async def send_message_scheduler(bot_token: str, chat_id: int, user_id: int, reminder_title: str):
    """
    Функция, которая отправляет запланированное сообщение пользователю.

    :param bot: Экземпляр бота для отправки сообщений.
    :param message: Исходное сообщение от пользователя, на основе которого отправляется напоминание.
    :param date: Словарь с данными о времени и интервалах напоминания.
    """
    bot = Bot(token=bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"@{user_id}\nЗавершите задание - {reminder_title}"
        )
    finally:
        await bot.session.close()
