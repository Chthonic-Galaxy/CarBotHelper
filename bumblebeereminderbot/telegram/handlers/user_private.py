"""
Модуль обработчиков для приватных сообщений пользователя.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from tzlocal import get_localzone
import json
import re

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
from io import BytesIO

from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandStart, or_f, StateFilter
from aiogram.utils.serialization import deserialize_telegram_object_to_python
from aiogram.types import PhotoSize
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.scene import Scene, on, ScenesManager
from aiogram.fsm.context import FSMContext

from bumblebeereminderbot.telegram.kbd.inline import get_callback_btns, Remove, View, Period
from bumblebeereminderbot.telegram.middlewares.scheduler import send_message_scheduler

import bumblebeereminderbot.database.requests as rq
from bumblebeereminderbot.utils.searcher import searcher

# Создание роутера для обработки приватных сообщений
user_private = Router()

# Получаем часовой пояс системы
local_tz = get_localzone()

# Константы для инлайн кнопок
BUTTONS = {
    "Profile": "Профиль",
    "Reminders": "Напоминания",
    "Notes": "Заметки",
    "Purchases": "Покупки",
    "Analytics": "Аналитика",
    "Remove": "Удалить",
    "Add": "Добавить",
    "View": "Просмотр",
    "Main": "В меню",
    "Back": "Назад",
}


# Регистрация обработчиков команд /menu и /start
@user_private.message(or_f(Command("menu"), CommandStart()))
async def start_menu(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Обработчик команд /menu и /start. Очищает состояние и входит в сцену главного меню.
    """
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
        Обработчик входа в сцену меню. Отправляет приветственное сообщение и кнопки меню.
        """
        # записываем tg_id пользователя и добавление в базу данных User
        await rq.set_user(tg_id=event.from_user.id)

        if isinstance(event, types.Message):
            # Удаление предыдущего сообщения и отправка меню
            await event.delete()
            await event.answer(
                text="Здравствуйте, вы в CarBotHelper!",
                reply_markup=get_callback_btns(
                    btns={
                        BUTTONS["Profile"]: "profile",
                        BUTTONS["Reminders"]: "reminder",
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
                        BUTTONS["Reminders"]: "reminder",
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
    async def goto_analisis(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену аналитики.
        """
        await self.wizard.goto(Analisis)

    @on.callback_query(F.data == "reminder")
    async def goto_reminders(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в сцену планировщика.
        """
        await self.wizard.goto(Reminders)

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass 

#=========Profile=========
class AddCar(StatesGroup):
    """
    Состояния для процесса добавления автомобиля.
    """
    name = State()
    edit_name = State()
    year = State()
    edit_year = State()

class Profile(Scene, state="profile"):
    """
    Сцена профиля пользователя.
    """

    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену профиля.  Отображает список автомобилей пользователя.
        """
        try:
            # Пытаемся удалить предыдущее сообщение
            if isinstance(event, types.Message):
                await event.message.delete()
        except:
            pass
        cars = [i for i in await rq.get_cars(tg_id=event.from_user.id)]

        message_text = f'У вас {len(cars)} машины.' or "У вас нет машин."
        buttons = {
            BUTTONS["Remove"]: "remove_auto",
            BUTTONS["Add"]: "add_auto",
            BUTTONS["View"]: "view_auto",
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
            await event.message.edit_text(
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

    @on.callback_query(F.data == "add_auto")
    async def add_auto(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса добавления автомобиля.  Переходит в состояние AddCar.name.
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
        Начало процесса удаления автомобиля.  Отображает список автомобилей для удаления.
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
        Удаление выбранного автомобиля.  Удаляет автомобиль из базы данных и обновляет список.
        """
        await rq.remove_car(car_id=callback_data.id)
        await self.wizard.retake()

    @on.callback_query(F.data == 'view_auto')
    async def view_cars(self, callback: types.CallbackQuery, state: FSMContext):
        cars = await rq.get_cars(callback.from_user.id)

        message_text = "Выберите автомобиль для подробной информации о нем."
        buttons = {f'{car.name}': View(id=car.car_id).pack() for car in cars}

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_callback_btns(btns={
                **buttons, **{"⬅️ Назад": "back"}
            })
        )
        await callback.answer()

    @on.callback_query(View.filter())
    async def view_car(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        car = await rq.get_car(callback_data.id)
        await state.update_data(edit_car=[car.car_id])

        message_text = f'{car.name} - {car.year} года выпуска.'

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_callback_btns(
                btns={
                    **{'Редактировать': 'edit'},
                    **{"⬅️ Назад": "back"}
                }
            )
        )
        await callback.answer()

    @on.callback_query(F.data == 'edit')
    async def edit_car(self, callback: types.CallbackQuery, state: FSMContext):
        await self.wizard.exit()
        await state.set_state(AddCar.edit_name)

        await callback.message.edit_text(text="Измените название автомобиля или нажмите пропустить.",
                                      reply_markup=get_callback_btns(btns={
                                          **{'Пропустить': 'next_name'},
                                          **{"⬅️ Назад": "back_profiler"}
                                      }))
        await callback.answer()

    @on.callback_query(F.data == "back")
    async def back(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к предыдущему состоянию.
        """
        await self.wizard.retake()

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass 

@user_private.callback_query(F.data == 'back_profiler')
async def back_profiler(callback: types.CallbackQuery, scenes: ScenesManager):
    await scenes.enter(Profile)

@user_private.message(AddCar.edit_name, F.text.regexp(r'^\w+$'))
@user_private.callback_query(F.data == 'next_name')
async def edit_name(event: types.Message | types.CallbackQuery, state: FSMContext):
    """
    Сохранение нового названия автомобиля и переход к вводу года.  Проверяет на уникальность названия.
    """
    data = await state.get_data()
    car = await rq.get_car(data['edit_car'][0])
    if isinstance(event, types.CallbackQuery):
        data['edit_car'].append(car.name)
        await state.set_state(AddCar.edit_year)
        await event.message.edit_text("Введите год авто или нажмите пропустить.",
                            reply_markup=get_callback_btns(
                                btns={
                                    **{'Пропустить': 'next_year'},
                                    **{"⬅️ Назад": "back_profiler"}
                                }
                            ))
        await event.answer()
    else:
        if not event.text.lower() == car.name.lower():
            data['edit_car'].append(event.text)
            await state.set_state(AddCar.edit_year)
            await event.answer("Введите год авто или нажмите пропустить.",
                               reply_markup=get_callback_btns(
                                   btns={
                                        **{'Пропустить': 'next_year'},
                                        **{"⬅️ Назад": "back_profiler"}
                                   }
                               ))
            await event.bot.delete_messages(
                chat_id=event.chat.id,
                message_ids=[event.message_id - 1,
                         event.message_id]
            )
        else:
            await event.answer(text="Название автомобиля уже существует. Введите снова.")
        
@user_private.message(AddCar.edit_year, F.text.regexp(r'^\d+$'))
@user_private.callback_query(F.data == 'next_year')
async def edit_year(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    """
    Сохранение года автомобиля и возврат в профиль.  Проверяет корректность года выпуска.
    """
    data = await state.get_data()
    car = await rq.get_car(data['edit_car'][0])
    if isinstance(event, types.CallbackQuery):
        data = await state.get_data()
        data["edit_car"].append(car.year)
        await rq.update_car(car_id=data["edit_car"][0], name=data["edit_car"][1], year=data["edit_car"][2])
        await scenes.enter(Profile)
    else:
        if 1900 <= int(event.text) <= datetime.now(local_tz).year:
            data = await state.get_data()
            data["edit_car"].append(event.text)
            await event.bot.delete_messages(
                chat_id=event.chat.id,
                message_ids=[event.message_id - 1,
                            event.message_id]
            )
            await rq.update_car(car_id=data["edit_car"][0], name=data["edit_car"][1], year=data["edit_car"][2])

            await scenes.enter(Profile)
        else:
            await event.answer(text="Автомобили с таким годом вымерли или еще не появились. Введите верные данные.")


@user_private.message(AddCar.name, F.text.regexp(r'^\w+$'))
async def add_auto_name(message: types.Message, state: FSMContext):
    """
    Сохранение названия автомобиля и переход к вводу года.  Проверяет на уникальность названия.
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
    Сохранение года автомобиля и возврат в профиль.  Проверяет корректность года выпуска.
    """
    if 1900 <= int(message.text) <= datetime.now(local_tz).year:
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

@user_private.message(or_f(AddCar.name, AddCar.edit_name))
async def incorrect_auto_name(message: types.Message):
    """
    Обработка некорректного ввода названия автомобиля.
    """
    await message.bot.delete_messages(
        chat_id=message.chat.id,
        message_ids=[message.message_id - 1,
                    message.message_id]
    )
    await message.answer(text="Введите название корректное вашего автомобиля.")

@user_private.message(or_f(AddCar.year, AddCar.edit_year))
async def incorrect_auto_year(message: types.Message):
    """
    Обработка некорректного ввода года автомобиля.
    """
    await message.bot.delete_messages(
        chat_id=message.chat.id,
        message_ids=[message.message_id - 1,
                    message.message_id]
    )
    await message.answer(text="Введите год выпуска вашего автомобиля.")

#=========Profile=========

#==========Notes==========
class SearchNote(StatesGroup):
    search = State()

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

    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену заметок.  Отображает список заметок пользователя.
        """
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

        notes = [i for i in await rq.get_notes(tg_id=event.from_user.id)]
        await state.update_data(notes=notes)

        message_text = '\n'.join(f'{i}: {note.note_title} {note.note_date}' for i, note in enumerate(notes, start=1)) or "У вас нет заметок."
        buttons = {
            "Удалить": "remove_note",
            "Добавить": "add_note",
            "Показать": "show_note",
            "Поиск": "search_note",
            "Main": "main_menu"
        } if notes else {
            "Добавить": "add_note",
            "Main": "main_menu"
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
        Начало процесса добавления заметки.  Переходит в состояние AddNote.title.
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
        Начало процесса удаления заметки.  Отображает список заметок для удаления.
        """
        data = await state.get_data()
        notes = data["notes"]
        btns = {f"{i}": Remove(id=note_pk.note_id).pack() for i, note_pk in enumerate(notes, start=1)}
        await callback.message.edit_text(
            text='\n'.join(f'{i}: {note.note_title} {note.note_date}' for i, note in enumerate(notes, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(Remove.filter())
    async def _remove_note(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        """
        Удаление выбранной заметки.  Удаляет заметку из списка и обновляет состояние.
        """
        try:
            await rq.remove_note(note_id=callback_data.id)
        except:  # Обработка потенциальной ошибки IndexError
            await callback.answer("Ошибка: заметка не найдена.")
            return

        await self.wizard.retake()

    @on.callback_query(F.data == "show_note")
    async def show_note(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса просмотра заметки. Отображает список заметок для просмотра.
        """
        data = await state.get_data()
        notes = data["notes"]
        btns = {f"{i+1}": View(id=i).pack() for i in range(len(notes))}
        await callback.message.edit_text(
            text='\n'.join(f'{i}: {note.note_title} {note.note_date}' for i, note in enumerate(notes, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(View.filter())
    async def _view_note(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        """
        Отображение выбранной заметки.  Показывает полное содержание заметки.
        """
        data = await state.get_data()
        notes = data["notes"]
        try:
            note = notes[callback_data.id]
            message_text = f"{note.note_title} {note.note_date}\n\n{note.note_description}"
        except IndexError:  # Обработка потенциальной ошибки IndexError
            await callback.answer("Ошибка: заметка не найдена.")
            return
        try:
            await callback.message.edit_text(
                text=message_text,
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back"}
                )
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                text=message_text,
                reply_markup=get_callback_btns(
                    btns={"⬅️ Назад": "back"}
                )
            )
        finally:
            await callback.answer()

    @on.callback_query(F.data == "search_note")
    async def search_note(self, callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(SearchNote.search)
        await callback.message.edit_text(
            text="Введите текст, и мы попробуем найти интересующие вас заметки:",
            reply_markup=get_callback_btns(
                btns={"⬅️ Назад": "back_notes"}
            )
        )
        await callback.answer()

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass 

@user_private.message(AddNote.title, F.text)
async def add_note_title(message: types.Message, state: FSMContext):
    """
    Сохранение заголовка заметки и переход к вводу описания.
    """
    
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
    
    existing_notes = await rq.get_notes(message.from_user.id)
    if not any(message.text.lower() == note.note_title.lower() for note in existing_notes):
        await state.update_data(add_note=[message.text])
        await state.set_state(AddNote.description)
        await message.answer("Введите текст заметки:")
    else:
        await message.answer(text="Такой заголовок заметки уже существует. Введите снова.")

@user_private.message(AddNote.title)
async def incorrect_note_title(message: types.Message):
    """
    Обработка некорректного ввода заголовка заметки.  Просит ввести текст.
    """
    await message.answer(text="Введите текст.")

@user_private.message(AddNote.description, F.text)
async def add_note_description(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Сохранение описания заметки и возврат в сцену заметок.
    Добавляет заметку в список и обновляет состояние.
    """
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
    
    data = await state.get_data()
    data_add_note = data.get("add_note", [])
    data_add_note.append(message.text)

    await rq.set_note(
                note_title=data_add_note[0],
                note_date=datetime.now(local_tz),
                tg_id=message.from_user.id,
                note_description=data_add_note[1]
            )

    del data["add_note"] # Удаление данных из FSMContext для соображений грамотного распоряжения памятью
    await state.set_data(data)
    await scenes.enter(Notes)

@user_private.message(AddNote.description)
async def incorrect_note_description(message: types.Message):
    """
    Обработка некорректного ввода описания заметки.  Просит ввести текст.
    """
    await message.answer(text="Введите текст.")


@user_private.callback_query(SearchNote.search, F.data == 'back_notes')
async def back_notes(callback: types.CallbackQuery, scenes: ScenesManager, state: FSMContext):
    """
    Обработчик для возврата в сцену покупок.
    """
    await callback.answer()
    await scenes.enter(Notes)
    
@user_private.message(SearchNote.search, F.text)
async def search_note_text(message: types.Message, state: FSMContext, scenes: ScenesManager):
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
    
    data = await state.get_data()
    notes: list[rq.Note] = data["notes"]
    targeted_notes = searcher(notes, message.text, ["note_title", "note_description"])
    message_text = ('\n'.join(f'{i}: {note.note_title} {note.note_date}' for i, note in enumerate(notes, start=1) if i-1 in targeted_notes) or
    "Ничего не найдено. Введите текст заметки снова:")
    if targeted_notes:
        btns = {f"{i+1}": View(id=i).pack() for i in targeted_notes}
        await message.answer(
            text=message_text,
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )
        await state.set_state("notes") # Мы просто ставим состояние на состояние сцены Notes, но мы не вызываем точку входа
    else:
        await message.answer(
            text=message_text,
            reply_markup=get_callback_btns(
                btns={"⬅️ Назад": "back_notes"}
            )
        )

@user_private.message(SearchNote.search)
async def search_note_text(message: types.Message):
    await message.answer("Введите текст.")

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
    Сцена управления покупками пользователя.
    """
    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену покупок. Отображает список покупок пользователя.
        """
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

        purchases = [i for i in await rq.get_purchases(tg_id=event.from_user.id)]

        message_text = "\n".join(f"{i}: {purchase.purchase_title} {purchase.purchase_date.strftime('%d %B %Y %H:%M')}" 
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
        Начало процесса добавления покупки. Переходит в состояние AddPurchases.title.
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
        """
        Начало процесса удаления покупки.  Отображает список покупок для удаления.
        """
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
        """
        Удаление выбранной покупки.  Удаляет покупку из базы данных и обновляет список.
        """
        await rq.remove_purchase(purchase_id=callback_data.id)
        await self.wizard.retake()

    @on.callback_query(F.data == 'view_purchase')
    async def view_purchases(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Просмотр всех покупок с фото и датой.
        """
        try:
            await callback.bot.delete_messages(
                chat_id=callback.from_user.id,
                message_ids=[
                    callback.message.message_id - 1,
                    callback.message.message_id
                    ]
            )
        except:
            pass
        purchases = [i for i in await rq.get_purchases(callback.from_user.id)]
        title_dicts = {purchase.purchase_id: f'{purchase.purchase_title} {purchase.purchase_date.strftime("%d %B %Y %H:%M")}' for purchase in purchases}
        photo_dicts = {purchase.purchase_id: json.loads(purchase.purchase_photo) for purchase in purchases if purchase.purchase_photo}

        for k, v in title_dicts.items():
            if k not in photo_dicts:
                await callback.message.answer(text=v)
            else:
                if isinstance(photo_dicts[k], list):
                    photos = [PhotoSize(**photo) for photo in photo_dicts[k]]  
                    for photo in photos:
                        await callback.message.answer_photo(photo.file_id, caption=v)
                else:
                    photo = PhotoSize(**photo_dicts[k])
                    await callback.message.answer_photo(photo.file_id, caption=v)
        await self.wizard.retake()

    @on.callback_query(F.data == 'search_purchase')
    async def search_purchases(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса поиска покупок. Переходит в состояние AddPurchases.search.
        """
        await self.wizard.exit()
        await state.set_state(AddPurchases.search)
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(
            text="Введите товар который вы бы хотели найти.",
            reply_markup=get_callback_btns(
                btns={"⬅️ Назад": "back_purchase"}
            )
        )
        await callback.answer()

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass 

@user_private.callback_query(AddPurchases.search, F.data == 'back_purchase')
async def back_purchases(callback: types.CallbackQuery, scenes: ScenesManager, state: FSMContext):
    """
    Обработчик для возврата в сцену покупок.
    """
    await callback.answer()
    await scenes.enter(Purchase)

@user_private.message(AddPurchases.search, F.text)
async def search_purchase(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Поиск покупок по названию.  Отображает найденные покупки.
    """
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
            if k not in photo_dicts:
                await message.answer(text=v)
            else:
                if isinstance(photo_dicts[k], list):
                    photos = [PhotoSize(**photo) for photo in photo_dicts[k]]  
                    for photo in photos:
                        await message.answer_photo(photo.file_id, caption=v)
                else:
                    photo = PhotoSize(**photo_dicts[k])
                    await message.answer_photo(photo.file_id, caption=v)
        await scenes.enter(Purchase)
    else:
        await message.answer("Такого товара нет среди покупок.\nВведите снова или нажмите кнопку назад.",
                                 reply_markup=get_callback_btns(btns={"⬅️ Назад": "back_purchase"}))

@user_private.message(AddPurchases.title, F.text)
async def add_title(message: types.Message, state: FSMContext):
    """
    Добавление названия покупки. Переходит в состояние AddPurchases.photo.  Проверяет на уникальность названия.
    """
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
    title_list = [i.purchase_title for i in await rq.get_purchases(tg_id=message.from_user.id)]
    if not any(message.text.lower() == title.lower() for title in title_list):
        await state.update_data(add_purchase=[message.text])
        await state.set_state(AddPurchases.photo)
        await message.answer("Если не хотите добавить фото товара или услуги\nпросто нажмите продолжить.",
                            reply_markup=get_callback_btns(btns={"Продолжить": "break"}))
    else:
        await message.answer("Введите уникальное название.")
 
@user_private.message(AddPurchases.photo)
@user_private.callback_query(F.data == 'break')
async def add_photo(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    """
    Добавление фото к покупке (опционально). Сохраняет покупку в базе данных и возвращается в сцену покупок.
    """
    data = await state.get_data()
    if isinstance(event, types.CallbackQuery):
        await rq.set_purchase(
            purchase_date=datetime.now(local_tz), 
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
            purchase_date=datetime.now(local_tz), 
            tg_id=event.from_user.id, 
            purchase_title=data.get('add_purchase')[0])
        await scenes.enter(Purchase)
    else:
        data['add_purchase'].append(event.photo[-1])
        await rq.set_purchase(
            purchase_date=datetime.now(local_tz),
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

@user_private.message(AddPurchases.title)
async def incorerct_add_title_purchase(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Возврат к вводу названия товара.
    """
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
    await message.answer("Некорректные данные названия товара. Введите в строку текст.")

@user_private.message(AddPurchases.search)
async def incorerct_search_purchase(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Возврат к запросу поиска товара.
    """
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
    await message.answer("Некорректные данные поиска. Введите в строку текст.")

#=========Analisis=========

# Вспомогательная функция для генерации аналитичекского графика
async def generate_analytics_graph(analytics_data, start_date, end_date):
    """
    Генерирует аналитический график на основе предоставленных данных.

    Args:
        analytics_data: Список объектов аналитики.
        start_date: Дата начала периода.
        end_date: Дата окончания периода.

    Returns:
        aiogram.types.BufferedInputFile: График в виде файла, или None, если данных нет.
    """
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

    # Plot 1: Ежедневные траты
    ax1.bar(dates, prices, width=0.8, align='center')
    ax1.set_xlabel("Дата")
    ax1.set_ylabel("Ежедневные траты")
    ax1.set_title("Ежедневные траты")
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.tick_params(axis='x', rotation=45)
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True))

    # Plot 2: Совокупные расходы
    ax2.plot(dates, cumulative_spending, marker='o', color='green')
    ax2.set_xlabel("Дата")
    ax2.set_ylabel("Совокупные расходы")
    ax2.set_title("Совокупные расходы за период времени")
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
    """
    Генерирует аналитический отчет на основе предоставленных данных.

    Args:
        analytics_data: Список объектов аналитики.
        start_date: Дата начала периода.
        end_date: Дата окончания периода.

    Returns:
        Tuple[str, aiogram.types.BufferedInputFile | None]: Текст отчета и график (или None, если данных нет).
    """
    report_graph = await generate_analytics_graph(analytics_data, start_date, end_date)

    filtered_data = [
        analytic
        for analytic in analytics_data
        if start_date <= analytic.analytics_date.date() <= end_date
    ]
    
    if not filtered_data:
        return "Нет данных за выбранный период.", None

    total_spent = sum(analytic.analytics_price for analytic in filtered_data)
    
    # Group expenses by category
    categories = defaultdict(float)
    for analytic in filtered_data:
        categories[analytic.analytics_title] += analytic.analytics_price
    
    # Find the day with the highest spending
    max_spending_day = max(filtered_data, key=lambda x: x.analytics_price, default=None) # added default=None to handle empty filtered_data
    
    # Calculate average daily spending
    days_count = (end_date - start_date).days + 1
    avg_daily_spending = total_spent / days_count
    
    report_text = f"Аналитический отчет\n"
    report_text += f"Период: {start_date} - {end_date}\n\n"
    report_text += f"Всего потрачено: {total_spent:.2f}\n"
    report_text += f"Средние траты в день: {avg_daily_spending:.2f}\n"

    if max_spending_day: # Check if max_spending_day is not None
        report_text += f"День с самыми большими тратами: {max_spending_day.analytics_date.date()} - {max_spending_day.analytics_price:.2f}\n\n"
    else:
        report_text += "День с самыми большими тратами: Нет данных.\n\n"

    report_text += "Траты по категориям:\n"
    for category, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (amount / total_spent) * 100
        report_text += f"- {category}: {amount:.2f} ({percentage:.1f}%)\n"
    
    report_text += "\nПоследние транзакции:\n"
    recent_transactions = sorted(filtered_data, key=lambda x: x.analytics_date, reverse=True)[:5]
    for analytic in recent_transactions:
        report_text += f"- {analytic.analytics_date.date()}: {analytic.analytics_title} - {analytic.analytics_price:.2f}\n"
        if analytic.analytics_description:
            report_text += f"  Описание: {analytic.analytics_description}\n"

    return report_text, report_graph


async def generate_and_send_report(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager, start_date, end_date):
    """
    Генерирует и отправляет аналитический отчет.

    Args:
        event: Событие (сообщение или callback query).
        state: FSMContext.
        scenes: ScenesManager.
        start_date: Дата начала периода.
        end_date: Дата окончания периода.
    """
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
    """
    Состояния для выбора периода отчета.
    """
    start_date = State()
    end_date = State()

class AddAData(StatesGroup):
    """
    Состояния для добавления данных аналитики.
    """
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
        Обработчик входа в сцену аналитики. Отображает общую информацию и список данных аналитики.
        """
        try:
            # Пытаемся удалить предыдущее сообщение
            await event.message.delete()
        except:
            pass
        analitics = [*(analitic for analitic in await rq.get_analytics(tg_id=event.from_user.id))]
        await state.update_data(adata=analitics)
        
        spended_money = sum(analitic.analytics_price for analitic in analitics)

        message_text = f"Вы всего потратили: {round(spended_money, 2)}\n" + "\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime('%d %B %Y %H:%M')}" for i, analitic in enumerate(analitics, start=1)) or "У вас нету данных для аналитики."
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
        """
        Начало процесса добавления данных аналитики. Переходит в состояние AddAData.title.
        """
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
        Начало процесса удаления данных аналитики. Отображает список данных для удаления.
        """
        data = await state.get_data()
        adata = data["adata"]
        btns = {f"{i}": Remove(id=adata_pk.analytics_id).pack() for i, adata_pk in enumerate(adata, start=1)}
        await callback.message.edit_text(
            text="\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime('%d %B %Y %H:%M')}" for i, analitic in enumerate(adata, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back_analisis"}},
                custom=True
            )
        )

    @on.callback_query(Remove.filter())
    async def _remove_note(self, callback: types.CallbackQuery, callback_data: Remove, state: FSMContext):
        """
        Удаление выбранных данных аналитики. Удаляет данные из базы данных и обновляет список.
        """
        await rq.remove_analytics(analytics_id=callback_data.id)
        await self.wizard.retake()
    
    @on.callback_query(F.data == "show_adata")
    async def show_adata(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса просмотра данных аналитики.  Отображает список данных для просмотра.
        """
        data = await state.get_data()
        adata = data["adata"]
        btns = {f"{i+1}": View(id=i).pack() for i in range(len(adata))}
        await callback.message.edit_text(
            text="\n".join(f"{i}: {analitic.analytics_title} {analitic.analytics_price} {analitic.analytics_date.strftime('%d %B %Y %H:%M')}" for i, analitic in enumerate(adata, start=1)),
            reply_markup=get_callback_btns(
                btns={**btns, **{"Получить отчёт": "get_analytic_report", "⬅️ Назад": "back_analisis"}},
                custom=True
            )
        )

    @on.callback_query(View.filter())
    async def _view_adata(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        """
        Отображение выбранных данных аналитики.  Показывает полное описание данных.
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
        """
        Обрабатывает callback query для генерации аналитического отчета.
        Предлагает выбрать период для отчета.
        """
        btns = {
            "Последние 7 дней": Period(period=7).pack(),
            "Последние 30 дней": Period(period=30).pack(),
            "Последние 90 дней": Period(period=90).pack(),
            "Произвольный период": Period(period="custom").pack(),
            "⬅️ Назад": "back_analisis"
        }
        
        await callback.message.edit_text(
            "Выберите период для аналитического отчета:",
            reply_markup=get_callback_btns(btns=btns, custom=True)
        )
        await callback.answer()
        
    @on.callback_query(Period.filter())
    async def handle_period_selection(self, callback: types.CallbackQuery, callback_data: Period, state: FSMContext, scenes: ScenesManager):
        """
        Обрабатывает выбор периода для отчета.
        Если выбран "custom", переходит к вводу начальной даты.
        Иначе генерирует и отправляет отчет.
        """
        period = callback_data.period
        if period == "custom":
            await state.set_state(PeriodSelection.start_date)
            await callback.message.edit_text("Введите начальную дату для отчета (YYYY-MM-DD):")
        else:
            days = int(period)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            await generate_and_send_report(callback, state, scenes, start_date, end_date)

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass


@user_private.message(PeriodSelection.start_date, F.text)
async def process_start_date(message: types.Message, state: FSMContext):
    """
    Обрабатывает ввод начальной даты для отчета.
    Переходит к вводу конечной даты.
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
    Обрабатывает ввод конечной даты и генерирует отчет.
    Проверяет, что начальная дата не позже конечной.
    """
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data["start_date"]
        
        if start_date <= end_date:
            analytics_data = data.get("adata", []) # добавлено .get для избежания keyError
            report_text, report_file = await generate_analytics_report(analytics_data, start_date, end_date)

            if report_file:
                    await message.answer_photo(photo=report_file, caption=report_text)
            else:
                await message.answer(report_text)

            await state.clear()
            await scenes.enter(Analisis)
        else:
            await message.answer(text="Начальная дата не может быть позже чем конечная.")
    except (ValueError, KeyError): # обрабатывает ValueError и KeyError
        await message.answer("Неверный формат даты. Пожалуйста, используйте YYYY-MM-DD.")



@user_private.message(AddAData.title, F.text)
async def add_adata_title(message: types.Message, state: FSMContext):
    """
    Добавление заголовка данных аналитики. Переходит в состояние AddAData.price.
    Проверяет на уникальность заголовка.
    """
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
    """
    Обработка некорректного ввода заголовка данных аналитики.  Просит ввести текст.
    """
    await message.answer("Введите текст.")

@user_private.message(AddAData.price, F.text)
async def add_adata_price(message: types.Message, state: FSMContext):
    """
    Добавление цены данных аналитики.  Переходит в состояние AddAData.description.
    Проверяет на числовой формат.
    """
    data = await state.get_data()
    adata = data.get("add_adata", []) # Изменено для предотвращения KeyError
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
    except (ValueError, TypeError): # обрабатываем ValueError и TypeError
        await message.answer(text="Введите число.")

@user_private.message(AddAData.price)
async def incorrect_adata_price(message: types.Message):
    """
    Обработка некорректного ввода цены данных аналитики.  Просит ввести число.
    """
    await message.answer("Введите число.")

@user_private.callback_query(F.data == "skip")
@user_private.message(StateFilter("*"), or_f(Command("пропустить", ignore_case=True), F.text.lower() == "пропустить"))
async def skip_adata_description(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    """
    Пропуск добавления описания данных аналитики. Сохраняет данные и возвращается в сцену аналитики.
    """
    await save_adata(event, state, scenes)

@user_private.message(AddAData.description, F.text)
async def add_adata_description(message: types.Message, state: FSMContext, scenes: ScenesManager):
    """
    Добавление описания данных аналитики.  Сохраняет данные и возвращается в сцену аналитики.
    Ограничивает длину описания 256 символами.
    """
    data = await state.get_data()
    adata = data.get("add_adata", []) # Изменено для предотвращения KeyError

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
    """
    Обработка некорректного ввода описания данных аналитики.  Просит ввести текст не более 256 символов.
    """
    await message.answer("Введите описание не больше чем на 256 символов. Текстом.")

async def save_adata(event: types.Message | types.CallbackQuery, state: FSMContext, scenes: ScenesManager):
    """
    Сохраняет данные аналитики в базу данных.  Очищает состояние и возвращается в сцену аналитики.
    """
    data = await state.get_data()
    adata: list = data.get("add_adata", []) #  Изменено для предотвращения KeyError
    
    await rq.set_analytics(
        analytics_title=adata[0],
        analytics_price=adata[1],
        analytics_description=adata[2] if len(adata) == 3 else None,
        analytics_date=datetime.now(local_tz),
        tg_id=event.from_user.id
    )
    data.pop("add_adata", None) # Безопасное удаление ключа 'add_adata' из data
    await state.set_data(data)
    await scenes.enter(Analisis)

#=========Analisis=========

#=========Reminders=========

class AddReminders(StatesGroup):
    """
    Состояния для добавления напоминаний.
    """
    title = State()
    description = State()
    date_reminder = State()


class Reminders(Scene, state="reminder"):
    """
    Сцена управления напоминаниями пользователя.
    """
    @on.message.enter()
    @on.callback_query.enter()
    async def on_enter(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """
        Обработчик входа в сцену напоминаний.  Отображает список автомобилей для выбора.
        """
        try:
            await event.message.delete()
        except:
            pass

        cars = await rq.get_cars(tg_id=event.from_user.id)

        message_text = "Добро пожаловать в раздел напоминаний.\nВыберите автомобиль, что бы перейти к задачам."
        buttons = {f'{car.name}': View(id=car.car_id).pack() for car in cars}

        if isinstance(event, types.Message):
            await event.answer(text=message_text, reply_markup=get_callback_btns(btns={**buttons, **{'В меню': 'main_menu'}}))
        else:
            await event.message.answer(text=message_text, reply_markup=get_callback_btns(btns={**buttons, **{'В меню': 'main_menu'}}))
            await event.answer()

    @on.callback_query(F.data == 'main_menu')
    async def got_menu(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Переход в главное меню.
        """
        await self.wizard.goto(Menu)

    @on.callback_query(View.filter())
    async def car_reminders(self, callback: types.CallbackQuery, callback_data: View, state: FSMContext):
        """
        Отображает напоминания для выбранного автомобиля.
        """
        reminders = await rq.get_reminders(car_id=callback_data.id)
        await state.update_data(car_id=callback_data.id)
        is_reminders = [reminder.reminder_title for reminder in reminders]
        reminder_text = f'У вас запланированно {len(is_reminders)} задач.' if is_reminders else 'У вас нет запланированных задач.'
        buttons = {
            **{
                'Добавить': 'add_reminder',
                'Удалить': 'remove_reminder',
                'Посмотреть задачи': 'view_reminder',
                '⬅️ Назад': 'back_reminder'}
            } if is_reminders else {
            **{
                'Добавить': 'add_reminder',
                '⬅️ Назад': 'back_reminder'}
            }
        
        await callback.message.edit_text(
            text=reminder_text,
            reply_markup=get_callback_btns(btns=buttons)
        )
        await callback.answer()

    @on.callback_query(F.data == 'back_reminder')
    async def back_reminder(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Возврат к списку автомобилей.
        """
        await self.wizard.retake()

    @on.callback_query(F.data == 'add_reminder')
    async def add_reminder(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса добавления напоминания.  Переходит в состояние AddReminders.title.
        """
        try:
            await callback.bot.delete_messages(
                chat_id=callback.from_user.id,
                message_ids=[callback.message.message_id] # Исправлено: удаляем только одно сообщение
            )
        except:
            pass
        await self.wizard.exit()
        await state.set_state(AddReminders.title)
        await callback.message.answer(text='Введите название задачи.')

    @on.callback_query(F.data == 'view_reminder')
    async def view_reminders(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Просмотр всех напоминаний для выбранного автомобиля.
        """
        data = await state.get_data()
        reminders = await rq.get_reminders(data['car_id'])
        message_text = '\n'.join(f'{i}. {reminder.reminder_title}\n'
                                 f'напомнить: {reminder.reminder_date.strftime("%d %B %Y %H:%M")}\n'
                                 f'описание: {reminder.reminder_description}\n\n' for i, reminder in enumerate(reminders, start=1))

        buttons = {'⬅️ Назад': 'back_reminder'}
        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_callback_btns(btns=buttons)
        )

    @on.callback_query(F.data == 'remove_reminder')
    async def remove_reminder(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Начало процесса удаления напоминания. Отображает список напоминаний для удаления.
        """
        data = await state.get_data()
        reminders = [i for i in await rq.get_reminders(car_id=data['car_id'])]
        message_text = '\n'.join(f'{i}. {reminder.reminder_title}' for i, reminder in enumerate(reminders, start=1))
        buttons = {f'{i}': Remove(id=reminder.reminder_id).pack() for i, reminder in enumerate(reminders, start=1)}

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_callback_btns(btns=buttons, custom=True) # добавлено custom=True
        )
        await callback.answer()

    @on.callback_query(Remove.filter())
    async def _remove_reminder(self, callback: types.CallbackQuery, state: FSMContext, callback_data: Remove):
        """
        Удаление выбранного напоминания.  Удаляет напоминание из базы данных и обновляет список.
        """
        await rq.remove_reminder(reminder_id=callback_data.id)
        await callback.answer(text='Данные задачи успешно удалены.')
        await self.wizard.retake()

    @on.callback_query.leave()
    @on.message.leave()
    async def leave(self, event: types.Message | types.CallbackQuery, state: FSMContext):
        """Действие при выходе из сцены."""
        pass 


@user_private.message(AddReminders.title, F.text.func(lambda text: text))
async def add_reminder_title(message: types.Message, state: FSMContext):
    """
    Добавление названия напоминания. Переходит в состояние AddReminders.description.
    """
    await state.update_data(add_title=message.text)
    try:
        await message.bot.delete_messages(
        chat_id=message.from_user.id,
        message_ids=[message.message_id - 1,
                     message.message_id]
    )
    except:
        pass
    await state.set_state(AddReminders.description)
    await message.answer('Введите описание задачи.')

@user_private.message(AddReminders.description, F.text.func(lambda text: text))
async def add_reminder_description(message: types.Message, state: FSMContext):
    """
    Добавление описания напоминания.  Переходит в состояние AddReminders.date_reminder.
    """
    await state.update_data(add_description=message.text)
    try:
        await message.bot.delete_messages(
        chat_id=message.from_user.id,
        message_ids=[message.message_id - 1,
                     message.message_id]
    )
    except:
        pass
    await state.set_state(AddReminders.date_reminder)
    await message.answer('Введите дату и время выполнения задачи.\nВ формате "2024-11-15 22:15"\n"Год-месяц-день часы:минуты"')

@user_private.message(
        AddReminders.date_reminder, 
        F.text.func(lambda text: re.findall(r'(\d+){4}-(\d+){2}-(\d+){2} (\d+){2}:(\d+){2}', text) # fixed regex for date format
                    and datetime.strptime(text, '%Y-%m-%d %H:%M')
                    .replace(tzinfo=local_tz) > datetime.now(local_tz)))
async def add_reminder_date(message: types.Message, state: FSMContext, scenes: ScenesManager, apscheduler: AsyncIOScheduler, bot: Bot):
    """
    Добавление даты и времени напоминания.  Сохраняет напоминание в базе данных и добавляет задачу в планировщик.
    """
    date_reminder = datetime.strptime(message.text, '%Y-%m-%d %H:%M').replace(tzinfo=local_tz)
    await state.update_data(add_date=date_reminder)
    data = await state.get_data()
    try:
        await message.bot.delete_messages(
        chat_id=message.from_user.id,
        message_ids=[message.message_id - 1,
                     message.message_id]
    )
    except:
        pass
    await rq.set_reminder(reminder_title=data['add_title'],
                          reminder_description=data['add_description'],
                          reminder_date=data['add_date'],
                          car_id=data['car_id'])
    
    # Добавляем задачу в планировщик
    data_id = json.dumps(deserialize_telegram_object_to_python(data))
    job = apscheduler.add_job(
        send_message_scheduler,
        trigger=DateTrigger(run_date=data['add_date']),
        kwargs={
            'bot_token': bot.token,
            'chat_id': message.chat.id,
            'fullname': message.from_user.full_name,
            'data': data_id
        },
        id=f"reminder_{message.from_user.id}_{data['add_title']}"
    )
    await scenes.enter(Reminders)

@user_private.message(AddReminders.title)
async def incorrect_title(message: types.Message, state: FSMContext):
    """
    Обработка некорректного ввода названия задачи.  Просит ввести корректное название.
    """
    try:
        await message.bot.delete_messages(
            chat_id=message.from_user.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
    except:
        pass
    await message.answer(text='Введите корректное название задачи.')

@user_private.message(AddReminders.description)
async def incorrect_description(message: types.Message, state: FSMContext):
    """
    Обработка некорректного ввода описания задачи.  Просит ввести корректное описание.
    """
    try:
        await message.bot.delete_messages(
            chat_id=message.from_user.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
    except:
        pass
    await message.answer(text='Введите корректное описание задачи.')

@user_private.message(AddReminders.date_reminder)
async def incorrect_date(message: types.Message, state: FSMContext):
    """
    Обработка некорректного ввода даты и времени.  Просит ввести корректную дату и время.
    """
    try:
        await message.bot.delete_messages(
            chat_id=message.from_user.id,
            message_ids=[message.message_id - 1,
                        message.message_id]
        )
    except:
        pass
    await message.answer(text='Введите корректную дату и время.')


#=========Reminders=========