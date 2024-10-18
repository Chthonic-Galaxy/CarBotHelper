"""
Модуль обработчиков для приватных сообщений пользователя.
"""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import json
import re

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from io import BytesIO

from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart, or_f, StateFilter
from aiogram.utils.serialization import deserialize_telegram_object_to_python
from aiogram.types import PhotoSize
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.scene import Scene, on, ScenesManager
from aiogram.fsm.context import FSMContext

from telegram.kbd.inline import get_callback_btns, Remove, View, Period

import database.requests as rq

# Создание роутера для обработки приватных сообщений
user_private = Router()

# Константы для инлайн кнопок
BUTTONS = {
    "Profile": "Профиль",
    "Reminders": "Напоминания",
    "Notes": "Заметки",
    "Purchases": "Покупки",
    "Analytics": "Аналитика",
    "Remove": "Удалить",
    "Add": "Добавить",
    "Main": "В меню",
    "Back": "Назад"
}


# Регистрация обработчиков команд /menu и /start
@user_private.message(or_f(Command("menu"), CommandStart()))
async def start_menu(message: types.Message, state: FSMContext, scenes: ScenesManager):
    await state.clear()
    await scenes.enter(Menu)


class Menu(Scene, state="main_menu"):
    """
    Сцена главного меню.
    """

    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену меню.
        """
        # записуем tg_id пользователя и добавление в базу данных User
        await rq.set_user(tg_id=event.from_user.id)

        if isinstance(event, types.Message):
            # Удаление предыдущего сообщения и отправка меню
            await event.delete()
            await event.answer(
                text="Здравствуйте, вы в CarBotHelper!",
                reply_markup=get_callback_btns(
                    btns={
                        BUTTONS["Profile"]: "profile",
                        BUTTONS["Reminders"]: "reminders",
                        BUTTONS["Notes"]: "notes",
                        BUTTONS["Purchases"]: "purchase",
                        BUTTONS["Analytics"]: "analisis",
                    }
                )
            )
        else:
            # Редактирование сообщения и отправка меню
            await event.message.edit_text(
                text="Здравствуйте, вы в CarBotHelper!",
                reply_markup=get_callback_btns(
                    btns={
                        BUTTONS["Profile"]: "profile",
                        BUTTONS["Reminders"]: "reminders",
                        BUTTONS["Notes"]: "notes",
                        BUTTONS["Purchases"]: "purchase",
                        BUTTONS["Analytics"]: "analisis",
                    }
                )
            )
            await event.answer()

    @on.callback_query(F.data == "profile")
    async def goto_profile(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену профиля.
        """
        await self.wizard.goto(Profile)

    @on.callback_query(F.data == "notes")
    async def goto_notes(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену заметок.
        """
        await self.wizard.goto(Notes)

    @on.callback_query(F.data == "purchase")
    async def goto_purchase(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену покупок.
        """
        await self.wizard.goto(Purchase)

    @on.callback_query(F.data == "analisis")
    async def goto_notes(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену аналитики.
        """
        await self.wizard.goto(Analisis)

#=========Profile=========
class AddCar(StatesGroup):
    """
    Состояния для процесса добавления автомобиля.
    """
    name = State()
    year = State()

class Profile(Scene, state="profile"):
    """
    Сцена профиля пользователя.
    """

    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену профиля.
        """
        try:
            # Пытаемся удалить предыдущее сообщение
            await event.message.delete()
        except:
            pass
        cars = [i for i in await rq.get_cars(tg_id=event.from_user.id)]

        message_text = '\n'.join(f'{i}: {car.name} {car.year}' for i, car in enumerate(cars, start=1)) or "У вас нет машин."
        buttons = {
            BUTTONS["Remove"]: "remove_auto",
            BUTTONS["Add"]: "add_auto",
            BUTTONS["Main"]: "main_menu"
        } if cars else {
            BUTTONS["Add"]: "add_auto",
            BUTTONS["Main"]: "main_menu"
        }

        if isinstance(event, types.Message):
            # Отправка информации об автомобилях
            await event.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
        else:
            # Отправка информации об автомобилях
            await event.message.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
            await event.answer()

    @on.callback_query(F.data == "main_menu")
    async def goto_main_menu(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в главное меню.
        """
        await self.wizard.goto(Menu)

    @on.callback_query(F.data == "back")
    async def back(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к предыдущему состоянию.
        """
        await self.wizard.retake()

    @on.callback_query(F.data == "add_auto")
    async def add_auto(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса добавления автомобиля.
        """
        await self.wizard.exit()
        await state.set_state(AddCar.name)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text="Введите название авто:")
        await callback.answer()

    @on.callback_query(F.data == "remove_auto")
    async def remove_auto(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса удаления автомобиля.
        """
        cars = [i for i in await rq.get_cars(tg_id=callback.from_user.id)]
        text = '\n'.join(f'{i}: {car.name} {car.year}' for i, car in enumerate(cars, start=1))
        btns = {f"{i}": f'{Remove(id=car.car_id).pack()}' for i, car in enumerate(cars, start=1)}
        await callback.message.edit_text(
            text=text,
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(Remove.filter())
    async def _remove_auto(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        """
        Удаление выбранного автомобиля.
        """
        await rq.remove_car(car_id=callback_data.id)
        await self.wizard.retake()

@user_private.message(AddCar.name, F.text.regexp(r'^\w+$'))
async def add_auto_name(message: types.Message, state: FSMContext):
    """
    Сохранение названия автомобиля и переход к вводу года.
    """
    existing_car = await rq.get_cars(message.from_user.id)
    if not any(message.text.lower() == car.name.lower() for car in existing_car):
        await state.update_data(add_car=[message.text])
        await state.set_state(AddCar.year)
        await message.answer("Введите год авто:")
        await message.bot.delete_messages(
            chat_id=message.chat.id,
            message_ids=[message.message_id - 1,
                         message.message_id]
        )
    else:
        await message.answer(text="Название автомобиля уже существует. Введите снова.")

@user_private.message(AddCar.year, F.text.regexp(r'^\d+$'))
async def add_auto_year(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Сохранение года автомобиля и возврат в профиль.
    """
    if 1900 <= int(message.text) <= datetime.now(timezone.utc).year:
        data = await state.get_data()
        data["add_car"].append(message.text)
        await message.bot.delete_messages(
            chat_id=message.chat.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
        await rq.set_car(name=data["add_car"][0], year=data["add_car"][1], tg_id=message.from_user.id)

        await scenes.enter(Profile)
    else:
        await message.answer(text="Автомобили с таким годом вымерли или еще не появились. Введите верные данные.")

@user_private.message(AddCar.name)
async def incorrect_auto_name(message: types.Message):
    """
    Обработка некорректного ввода года автомобиля.
    """
    await message.answer(text="Введите название корректное вашего автомобиля.")

@user_private.message(AddCar.year)
async def incorrect_auto_year(message: types.Message):
    """
    Обработка некорректного ввода года автомобиля.
    """
    await message.answer(text="Введите год выпуска вашего автомобиля.")

#=========Profile=========

#==========Notes==========
class AddNote(StatesGroup):
    """
    Состояния для процесса добавления заметки.
    """
    title = State()
    description = State()

class Notes(Scene, state="notes"):
    """
    Сцена управления заметками пользователя.
    """

    @on.callback_query.enter()
    @on.message.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену заметок.
        """
        try:
            # Пытаемся удалить предыдущее сообщение
            await event.message.delete()
        except:
            pass
        data = await state.get_data()
        notes = data["notes"]

        message_text = f"У вас {'нету заметок.' if not notes else '\n'.join(f'{i+1}. {title[0]}' for i, title in enumerate(notes))}"
        buttons = {
            "Удалить": "remove_note",
            "Добавить": "add_note",
            "Показать": "show_note",
            "Main": "main_menu"
        } if notes else {
            "Добавить": "add_note",
            "Main": "main_menu"
        }

        if isinstance(event, types.Message):
            # Отправка информации о заметках
            await event.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
        else:
            # Отправка информации о заметках
            await event.message.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
            await event.answer()

    @on.callback_query(F.data == "main_menu")
    async def goto_main_menu(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в главное меню.
        """
        await self.wizard.goto(Menu)

    @on.callback_query(F.data == "back")
    async def back(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к предыдущему состоянию.
        """
        await self.wizard.retake()

    @on.callback_query(F.data == "add_note")
    async def add_note(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса добавления заметки.
        """
        await self.wizard.exit()
        await state.set_state(AddNote.title)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text="Введите заголовок заметки:")
        await callback.answer()

    @on.callback_query(F.data == "remove_note")
    async def remove_note(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса удаления заметки.
        """
        data = await state.get_data()
        notes = data["notes"]
        btns = {f"{i+1}": Remove(id=i).pack() for i in range(len(notes))}
        await callback.message.edit_text(
            text="\n".join(f"{i+1}. {title[0]}" for i, title in enumerate(notes)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(Remove.filter())
    async def _remove_note(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        """
        Удаление выбранной заметки.
        """
        data = await state.get_data()
        data["notes"].pop(callback_data.id)
        await state.update_data(notes=data["notes"])
        await self.wizard.retake()

    @on.callback_query(F.data == "show_note")
    async def show_note(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса просмотра заметки.
        """
        data = await state.get_data()
        notes = data["notes"]
        btns = {f"{i+1}": View(id=i).pack() for i in range(len(notes))}
        await callback.message.edit_text(
            text="\n".join(f"{i+1}. {title[0]}" for i, title in enumerate(notes)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(View.filter())
    async def _view_note(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        """
        Отображение выбранной заметки.
        """
        data = await state.get_data()
        note = data["notes"][callback_data.id]
        try:
            await callback.message.edit_text(
                text=note[1],
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back"}
                )
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                text=note[1],
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back"}
                )
            )
        finally:
            await callback.answer()

@user_private.message(AddNote.title, F.text)
async def add_note_title(message: types.Message, state: FSMContext):
    """
    Сохранение заголовка заметки и переход к вводу описания.
    """
    await state.update_data(add_note=[message.text])
    await state.set_state(AddNote.description)
    await message.answer("Введите текст заметки:")

@user_private.message(AddNote.title)
async def incorrect_note_title(message: types.Message):
    """
    Обработка некорректного ввода заголовка заметки.
    """
    await message.answer(text="Введите текст.")

@user_private.message(AddNote.description, F.text)
async def add_note_description(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Сохранение описания заметки и возврат в сцену заметок.
    """
    data = await state.get_data()
    data["add_note"].append(message.text)
    data["notes"].append(tuple(data["add_note"]))
    await state.update_data(notes=data["notes"])
    await scenes.enter(Notes)

@user_private.message(AddNote.description)
async def incorrect_note_description(message: types.Message):
    """
    Обработка некорректного ввода описания заметки.
    """
    await message.answer(text="Введите текст.")

#==========Notes==========


#========Purchases========
class AddPurchases(StatesGroup):
    """
    Состояния для процесса добавления покупок.
    """
    title = State()
    photo = State()
    back = State()
    search = State()

class Purchase(Scene, state='purchase'):
    """
    Сцена управления заметками пользователя.
    """
    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену покупок.
        """
        try:
            event.message.delete()
        except:
            pass

        purchases = [i for i in await rq.get_purchases(tg_id=event.from_user.id)]

        message_text = "\n".join(f"{i}: {purchase.purchase_title} {purchase.purchase_date.strftime("%d %B %Y %H:%M")}" 
                                 for i, purchase in enumerate(purchases, start=1)) or "У вас нет покупок."

        buttons = {
            "Удалить покупку": "remove_purchase",
            "Добавить покупку": "add_purchase",
            "Просмотр всех покупок": "view_purchase",
            "Поиск покупок": "search_purchase",
            "В меню": "main_menu"
        } if purchases else {
            "Добавить покупку": "add_purchase",
            "В меню": "main_menu"
        }

        try:
            if isinstance(event, types.Message):
                await event.edit_text(
                    text=message_text,
                    reply_markup=get_callback_btns(btns=buttons)
                )
            else:
                await event.message.edit_text(
                    text=message_text,
                    reply_markup=get_callback_btns(btns=buttons)
                )
                await event.answer()
        except:                
            if isinstance(event, types.Message):
                await event.answer(
                    text=message_text,
                    reply_markup=get_callback_btns(btns=buttons)
                )
            else:
                await event.message.answer(
                    text=message_text,
                    reply_markup=get_callback_btns(btns=buttons)
                )
                await event.answer()

        
    @on.callback_query(F.data == 'main_menu')
    async def goto_main_menu(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в главное меню.
        """
        await self.wizard.goto(Menu)

    @on.callback_query(F.data == 'back_purchase')
    async def goto_back(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к предыдущему состоянию.
        """
        await self.wizard.retake()

    @on.callback_query(F.data == 'add_purchase')
    async def add_purchase(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса добавления покупку.
        """
        await self.wizard.exit()
        await state.set_state(AddPurchases.title)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text="Введите название товара или услуги.")
        await callback.answer()

    @on.callback_query(F.data == 'remove_purchase')
    async def remove_purchase(self, callback: types.CallbackQuery, state: FSMContext):
        purchases = [i for i in await rq.get_purchases(tg_id=callback.from_user.id)]
        message_text = '\n'.join(f'{i}: {purchase.purchase_title} {purchase.purchase_date}' for i, purchase in enumerate(purchases, start=1))
        buttons = {f'{i}': Remove(id=purchase.purchase_id).pack() for i, purchase in enumerate(purchases, start=1)}
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_callback_btns(
                btns={**buttons, **{"⬅️ Назад": "back_purchase"}},
                custom=True)
        )
    
    @on.callback_query(Remove.filter())
    async def _remove_purchase(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        await rq.remove_purchase(purchase_id=callback_data.id)
        await self.wizard.retake()

    @on.callback_query(F.data == 'view_purchase')
    async def view_purchases(self, callback: types.CallbackQuery, state: FSMContext):
        try:
            await callback.message.delete()
        except:
            pass
        purchases = [i for i in await rq.get_purchases(callback.from_user.id)]
        title_dicts = {purchase.purchase_id: f'{purchase.purchase_title} {purchase.purchase_date.strftime("%d %B %Y %H:%M")}' for purchase in purchases}
        photo_dicts = {purchase.purchase_id: json.loads(purchase.purchase_photo) for purchase in purchases if purchase.purchase_photo}

        for k, v in title_dicts.items():
            if k in photo_dicts:
                if isinstance(photo_dicts[k], list):
                    photos = [PhotoSize(**photo) for photo in photo_dicts[k]]  
                    for photo in photos:
                        if photo.height == 1280:
                            await callback.message.answer_photo(photo.file_id, caption=v)
                else:
                    photo = PhotoSize(photo_dicts[k])
                    if photo.height == 1280:
                            await callback.message.answer_photo(photo.file_id, caption=v)
        for k, v in title_dicts.items():
            if k not in photo_dicts:
                await callback.message.answer(text=v)
        await self.wizard.retake()

    @on.callback_query(F.data == 'search_purchase')
    async def search_purchases(self, callback: types.CallbackQuery, state: FSMContext):
        await self.wizard.exit()
        await state.set_state(AddPurchases.search)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text="Введите товар который вы бы хотели найти.")
        await callback.answer()

@user_private.message(AddPurchases.search)
async def search_purchase(message: types.Message, state: FSMContext, scenes: ScenesManager):
        try:
            await message.bot.delete_messages(
                chat_id=message.from_user.id,
                message_ids=[
                    message.message_id - 1,
                    message.message_id
                    ]
            )
        except:
            pass
        purchases = [i for i in await rq.get_purchases(message.from_user.id)]
        purchases_filter = [i for i in purchases if re.search(message.text.lower(), i.purchase_title.lower())]
        title_dicts = {purchase.purchase_id: f'{purchase.purchase_title} {purchase.purchase_date.strftime("%d %B %Y %H:%M")}' for purchase in purchases_filter}
        photo_dicts = {purchase.purchase_id: json.loads(purchase.purchase_photo) for purchase in purchases_filter if purchase.purchase_photo}

        if title_dicts:
            for k, v in title_dicts.items():
                if k in photo_dicts:
                    if isinstance(photo_dicts[k], list):
                        photos = [PhotoSize(**photo) for photo in photo_dicts[k]]  
                        for photo in photos:
                            if photo.height == 1280:
                                await message.answer_photo(photo.file_id, caption=v)
                    else:
                        photo = PhotoSize(**photo_dicts[k])
                        if photo.height == 1280:
                                await message.answer_photo(photo.file_id, caption=v)
            for k, v in title_dicts.items():
                if k not in photo_dicts:
                    await message.answer(text=v)
            await scenes.enter(Purchase)
        else:
            await message.answer("Такого товара нет среди покупок.\nВведите снова или нажмите кнопку назад.",
                                 reply_markup=get_callback_btns(btns={**{"⬅️ Назад": "back_purchase"}}))
            
@user_private.callback_query(F.data == 'back_purchase')
async def back_search(callback: types.CallbackQuery, scenes: ScenesManager, state: FSMContext):
    """
    Обработчик для возврата в сцену.
    """
    await callback.answer()
    await scenes.enter(Purchase)

@user_private.message(AddPurchases.title)
async def add_title(message: types.Message, state: FSMContext):
    title_list = [i.purchase_title for i in await rq.get_purchases(tg_id=message.from_user.id)]
    if not any(message.text.lower() == title.lower() for title in title_list):
        await state.update_data(add_purchase=[message.text])
        await message.bot.delete_messages(
            chat_id=message.from_user.id,
            message_ids=[
                message.message_id - 1,
                message.message_id
            ]
        )
        await state.set_state(AddPurchases.photo)
        await message.answer("Если не хотите добавить фото товара или услуги\nпросто нажмите продолжить.",
    reply_markup=get_callback_btns(btns={"Продолжить": "break"}))
    else:
        await message.answer("Введите уникальное название.")
    
@user_private.message(AddPurchases.photo)
@user_private.callback_query(F.data == 'break')
async def add_photo(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    data = await state.get_data()
    if isinstance(event, types.CallbackQuery):
        await rq.set_purchase(
            purchase_date=datetime.now(timezone.utc), 
            tg_id=event.from_user.id, 
            purchase_title=data.get('add_purchase')[0])
        await scenes.enter(Purchase)
    elif not event.photo:
        try:
            await event.bot.delete_messages(
                chat_id=event.from_user.id,
                message_ids=[
                    event.message_id - 1,
                    event.message_id
                ]
            )
        except:
            pass
        await rq.set_purchase(
            purchase_date=datetime.now(timezone.utc), 
            tg_id=event.from_user.id, 
            purchase_title=data.get('add_purchase')[0])
        await scenes.enter(Purchase)
    else:
        data['add_purchase'].append(event.photo)
        await rq.set_purchase(
            purchase_date=datetime.now(timezone.utc),
            tg_id=event.from_user.id, 
            purchase_title=data.get('add_purchase')[0],
            purchase_photo=json.dumps(deserialize_telegram_object_to_python(data.get('add_purchase')[1])))
        try:
            await event.bot.delete_messages(
                chat_id=event.from_user.id,
                message_ids=[
                    event.message_id - 1,
                    event.message_id
                ]
            )
        except:
            pass
        await scenes.enter(Purchase)


#=========Analisis=========

# Вспомогательная функция для генерации аналитичекского графика
async def generate_analytics_graph(analytics_data, start_date, end_date):
    filtered_data = [
        analytic
        for analytic in analytics_data
        if start_date <= analytic.analytics_date.date() <= end_date
    ]
    if not filtered_data:
        return None

    # Sort data by date
    filtered_data.sort(key=lambda x: x.analytics_date)

    # Create a dictionary to store daily spending
    daily_spending = defaultdict(float)
    for analytic in filtered_data:
        date = analytic.analytics_date.date()
        daily_spending[date] += analytic.analytics_price

    # Generate a list of all dates in the range
    all_dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

    # Prepare data for plotting
    dates = all_dates
    prices = [daily_spending[date] for date in all_dates]
    cumulative_spending = [sum(prices[:i+1]) for i in range(len(prices))]

    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Daily spending
    ax1.bar(dates, prices, width=0.8, align='center')
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Daily Spending")
    ax1.set_title("Daily Spending")
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.tick_params(axis='x', rotation=45)
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Plot 2: Cumulative spending
    ax2.plot(dates, cumulative_spending, marker='o', color='green')
    ax2.set_xlabel("Date")
    ax2.set_ylabel("Cumulative Spending")
    ax2.set_title("Cumulative Spending Over Time")
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close(fig)

    return types.BufferedInputFile(buf.read(), filename="report.png")

# Improved function for generating analytics report
async def generate_analytics_report(analytics_data, start_date, end_date):
    report_graph = await generate_analytics_graph(analytics_data, start_date, end_date)

    filtered_data = [
        analytic
        for analytic in analytics_data
        if start_date <= analytic.analytics_date.date() <= end_date
    ]
    
    if not filtered_data:
        return "No data available for the selected period.", None

    total_spent = sum(analytic.analytics_price for analytic in filtered_data)
    
    # Group expenses by category
    categories = defaultdict(float)
    for analytic in filtered_data:
        categories[analytic.analytics_title] += analytic.analytics_price
    
    # Find the day with the highest spending
    max_spending_day = max(filtered_data, key=lambda x: x.analytics_price)
    
    # Calculate average daily spending
    days_count = (end_date - start_date).days + 1
    avg_daily_spending = total_spent / days_count
    
    report_text = f"Analytics Report\n"
    report_text += f"Period: {start_date} to {end_date}\n\n"
    report_text += f"Total Spent: {total_spent:.2f}\n"
    report_text += f"Average Daily Spending: {avg_daily_spending:.2f}\n"
    report_text += f"Highest Spending Day: {max_spending_day.analytics_date.date()} - {max_spending_day.analytics_price:.2f}\n\n"
    
    report_text += "Spending by Category:\n"
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_spent) * 100
        report_text += f"- {category}: {amount:.2f} ({percentage:.1f}%)\n"
    
    report_text += "\nRecent Transactions:\n"
    for analytic in sorted(filtered_data, key=lambda x: x.analytics_date, reverse=True)[:5]:
        report_text += f"- {analytic.analytics_date.date()}: {analytic.analytics_title} - {analytic.analytics_price:.2f}\n"
        if analytic.analytics_description:
            report_text += f"  Description: {analytic.analytics_description}\n"

    return report_text, report_graph


async def generate_and_send_report(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager, start_date, end_date):
        data = await state.get_data()
        analytics_data = data.get("adata", [])

        report_text, report_file = await generate_analytics_report(analytics_data, start_date, end_date)

        if isinstance(event, types.Message):
            if report_file:
                await event.answer_photo(photo=report_file, caption=report_text)
            else:
                await event.answer(report_text)
        else:
            if report_file:
                await event.message.answer_photo(photo=report_file, caption=report_text)
            else:
                await event.message.answer(report_text)
                await event.answer()

        await state.clear()
        await scenes.enter(Analisis)


class PeriodSelection(StatesGroup):
    start_date = State()
    end_date = State()

class AddAData(StatesGroup):
    title = State()
    price = State()
    description = State()
    

class Analisis(Scene, state="analysis"):
    """
    Сцена управления аналитикой пользователя.
    """
    
    @on.callback_query.enter()
    @on.message.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену аналитики.
        """
        try:
            # Пытаемся удалить предыдущее сообщение
            await event.message.delete()
        except:
            pass
        analitics = [*(analitic for analitic in await rq.get_analytics(tg_id=event.from_user.id))]
        await state.update_data(adata=analitics)
        
        spended_money = sum(analitic.analytics_price for analitic in analitics)

        message_text = f"Вы всего потратили: {round(spended_money, 2)}\n" + "\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime("%d %B %Y %H:%M")}" for i, analitic in enumerate(analitics, start=1)) or "У вас нету данных для аналитики."
        buttons = {
            "Удалить": "remove_adata",
            "Добавить": "add_adata",
            "Показать": "show_adata",
            "В меню": "main_menu"
        } if analitics else {
            "Добавить": "add_adata",
            "В меню": "main_menu"
        }

        if isinstance(event, types.Message):
            # Отправка информации о заметках
            await event.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
        else:
            # Отправка информации о заметках
            await event.message.answer(
                text=message_text,
                reply_markup=get_callback_btns(btns=buttons)
            )
            await event.answer()

    @on.callback_query(F.data == "main_menu")
    async def goto_main_menu(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в главное меню.
        """
        await self.wizard.goto(Menu)

    @on.callback_query(F.data == "back_analisis")
    async def back_analisis(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к предыдущему состоянию.
        """
        await self.wizard.retake()
        
    @on.callback_query(F.data == "add_adata")
    async def add_adata(self, callback: types.CallbackQuery, state: FSMContext):
        await self.wizard.exit()
        await state.set_state(AddAData.title)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text="Введите заголовок новых данных:")
        await callback.answer()
    
    @on.callback_query(F.data == "remove_adata")
    async def remove_adata(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса удаления данных аналитики.
        """
        data = await state.get_data()
        adata = data["adata"]
        btns = {f"{i}": Remove(id=adata_pk.analytics_id).pack() for i, adata_pk in enumerate(adata, start=1)}
        await callback.message.edit_text(
            text="\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime("%d %B %Y %H:%M")}" for i, analitic in enumerate(adata, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back_analisis"}},
                custom=True
            )
        )

    @on.callback_query(Remove.filter())
    async def _remove_note(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        """
        Удаление выбранных данных аналитики.
        """
        await rq.remove_analytics(analytics_id=callback_data.id)
        await self.wizard.retake()
    
    @on.callback_query(F.data == "show_adata")
    async def show_adata(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса просмотра данных аналитики.
        """
        data = await state.get_data()
        adata = data["adata"]
        btns = {f"{i+1}": View(id=i).pack() for i in range(len(adata))}
        await callback.message.edit_text(
            text="\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime("%d %B %Y %H:%M")}" for i, analitic in enumerate(adata, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"Получить отчёт": "get_analytic_report", "⬅️ Назад": "back_analisis"}},
                custom=True
            )
        )

    @on.callback_query(View.filter())
    async def _view_adata(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        """
        Отображение выбранных данных аналитики.
        """
        data = await state.get_data()
        adata = data["adata"][callback_data.id]
        try:
            await callback.message.edit_text(
                text=adata.analytics_description,
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back_analisis"}
                )
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                text=adata.analytics_description,
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back_analisis"}
                )
            )
        finally:
            await callback.answer()
            
    @on.callback_query(F.data == "get_analytic_report")
    async def get_analytic_report(self, callback: types.CallbackQuery, state: FSMContext):
        """Handles the callback query to generate an analytic report."""
        btns = {
            "Last 7 days": Period(period=7).pack(),
            "Last 30 days": Period(period=30).pack(),
            "Last 90 days": Period(period=90).pack(),
            "Custom period": Period(period="custom").pack(),
            "⬅️ Назад": "back_analisis"
        }
        
        await callback.message.edit_text(
            "Please select a period for the analytic report:",
            reply_markup=get_callback_btns(btns=btns, custom=True)
        )
        await callback.answer()
        
    @on.callback_query(Period.filter())
    async def handle_period_selection(self, callback: types.CallbackQuery, callback_data: Period, state: FSMContext, scenes: ScenesManager):
        period = callback_data.period
        if period == "custom":
            await state.set_state(PeriodSelection.start_date)
            await callback.message.edit_text("Enter the start date for the report (YYYY-MM-DD):")
        else:
            days = int(period)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            await generate_and_send_report(callback, state, scenes, start_date, end_date)

@user_private.message(PeriodSelection.start_date, F.text)
async def process_start_date(message: types.Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)
        await state.set_state(PeriodSelection.end_date)
        await message.answer("Enter the end date for the report (YYYY-MM-DD):")
    except ValueError:
        await message.answer("Invalid date format. Please use YYYY-MM-DD.")

@user_private.message(PeriodSelection.end_date, F.text)
async def process_end_date(message: types.Message, state: FSMContext, scenes: ScenesManager):
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data["start_date"]
        
        if start_date <= end_date:
            await generate_and_send_report(message, state, scenes, start_date, end_date)
        else:
            await message.answer("Start date cannot be later than end date.")
    except ValueError:
        await message.answer("Invalid date format. Please use YYYY-MM-DD.")
        
        
@user_private.message(PeriodSelection.start_date, F.text)
async def process_start_date(message: types.Message, state: FSMContext):
    """
    Processes the start date input for the report.
    """
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)
        await state.set_state(PeriodSelection.end_date)
        await message.answer("Введите конечную дату для отчета (YYYY-MM-DD):")
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте YYYY-MM-DD.")

@user_private.message(PeriodSelection.end_date, F.text)
async def process_end_date(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Processes the end date input and generates the report.
    """
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data["start_date"]
        
        if start_date <= end_date:
            analytics_data = data["adata"]  # Correctly access analytics data

            report_text, report_file = await generate_analytics_report(analytics_data, start_date, end_date)

            if report_file:  # If a report file (e.g. image) was generated
                    await message.answer_photo(photo=report_file, caption=report_text) # Sending file and text
            else:
                await message.answer(report_text)

            await state.clear()
            await scenes.enter(Analisis)
        else:
            await message.answer(text="Начальная дата не может быть позже чем конечная.")
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте YYYY-MM-DD.")



@user_private.message(AddAData.title, F.text)
async def add_adata_title(message: types.Message, state: FSMContext):
    
    existing_anaitics = await rq.get_analytics(tg_id=message.from_user.id)
        
    if not any(analitic.analytics_title.lower() == message.text.lower() for analitic in existing_anaitics):
        await state.update_data(add_adata=[message.text])
        await state.set_state(AddAData.price)
        await message.answer("Введите цену:")
        await message.bot.delete_messages(
            chat_id=message.chat.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
    else:
        await message.answer(text="Такой заголовок уже существует. Введите снова.")
        
@user_private.message(AddAData.title)
async def incorrect_adata_title(message: types.Message):
    message.answer("Введите текст.")

@user_private.message(AddAData.price, F.text)
async def add_adata_price(message: types.Message, state: FSMContext):
    
    data = await state.get_data()
    adata = data["add_adata"]
    try:
        price = float(message.text.replace(",", ".", 1))
        
        adata.append(price)
        
        await state.update_data(add_adata=adata)
        await state.set_state(AddAData.description)
        await message.answer(
                text="Введите описание до 256 символов или отправь команду `пропустить`:",
                reply_markup=get_callback_btns(btns={"Пропустить": "skip"})
            )
        await message.bot.delete_messages(
            chat_id=message.chat.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
    except:
        await message.answer(text="Введите число.")

@user_private.message(AddAData.price)
async def incorrect_adata_price(message: types.Message):
    message.answer("Введите число.")

@user_private.callback_query(F.data == "skip")
@user_private.message(StateFilter("*"), or_f(Command("пропустить", ignore_case=True), F.text.lower() == "пропустить"))
async def skip_adata_description(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    await save_adata(event, state, scenes)

@user_private.message(AddAData.description, F.text)
async def add_adata_description(message: types.Message, state: FSMContext, scenes: ScenesManager):
    
    data = await state.get_data()
    adata = data["add_adata"]
    if len(message.text) <= 256:
        adata.append(message.text)
        
        await state.update_data(add_adata=adata)
        await message.bot.delete_messages(
            chat_id=message.chat.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
        await save_adata(message, state, scenes)
    else:
        await message.answer(text="Введите описание не больше чем на 256 символов.")

@user_private.message(AddAData.description)
async def incorrect_adata_description(message: types.Message):
    message.answer("Введите описание не больше чем на 256 символов. Текстом.")

async def save_adata(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    data = await state.get_data()
    adata: list = data["add_adata"]
    
    await rq.set_analytics(
        analytics_title=adata[0],
        analytics_price=adata[1],
        analytics_description=adata[2] if len(adata) == 3 else None,
        analytics_date=datetime.now(timezone.utc),
        tg_id=event.from_user.id
    )
    del data["add_adata"] # Удаление данных из FSMContext для соображений грамотного распоряжения памятью
    await state.set_data(data)
    await scenes.enter(Analisis)

@user_private.callback_query(F.data == 'back_analisis')
async def back_search(callback: types.CallbackQuery, scenes: ScenesManager, state: FSMContext):
    """
    Обработчик для возврата в сцену.
    """
    await callback.answer()
    await scenes.enter(Analisis)

#=========Analisis=========
