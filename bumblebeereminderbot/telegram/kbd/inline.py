from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardBuilder

from utils.create_dicts import super_dicts_creator

# Классы для обработки callback_data кнопок (Callback Factory)
class Remove(CallbackData, prefix="remove"):
    id: int

class View(CallbackData, prefix="view"):
    id: int

def get_callback_btns(
    *,
    btns: dict[str, str] | dict,
    sizes: tuple[int] = (2,),
    custom: bool = False
):
    """
    Генерирует инлайн-клавиатуру с заданными кнопками.

    :param btns: Словарь с текстом кнопки и данными callback_data.
    :param sizes: Размеры клавиатуры.
    :param custom: Флаг использования кастомной генерации клавиатуры.
    :return: Объект InlineKeyboardMarkup.
    """
    keyboard = InlineKeyboardBuilder()

    if not custom:
        # Если не используется кастомная генерация, добавляем кнопки напрямую
        for text, data in btns.items():
            keyboard.add(InlineKeyboardButton(text=text, callback_data=data))
    else:
        # Если используется кастомная генерация, используем функцию super_dicts_creator
        for row in super_dicts_creator(btns):
            keyboard.row(*[InlineKeyboardButton(text=text, callback_data=data) for text, data in row.items()])

    return keyboard.adjust(*sizes).as_markup()
