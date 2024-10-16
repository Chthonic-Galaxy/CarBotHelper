"""
Модуль обработчиков для приватных сообщений пользователя.
"""

from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart, or_f, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.scene import Scene, on, ScenesManager
from aiogram.fsm.context import FSMContext

from telegram.kbd.inline import get_callback_btns, Remove, View

import database.requests as rq

# Создание роутера для обработки приватных сообщений
user_private = Router()

# Константы для инлайн кнопок
BUTTONS = {
    "Profile": "Профиль",
    "Reminders": "Напоминания",
    "Notes": "Заметки",
    "Good_purchases": "Хорошие покупки",
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
                text="Здравствуйте, вы в AvtoBot'e!",
                reply_markup=get_callback_btns(
                    btns={
                        BUTTONS["Profile"]: "profile",
                        BUTTONS["Reminders"]: "reminders",
                        BUTTONS["Notes"]: "notes",
                        BUTTONS["Good_purchases"]: "good_purchases",
                        BUTTONS["Analytics"]: "analisis",
                    }
                )
            )
        else:
            # Редактирование сообщения и отправка меню
            await event.message.edit_text(
                text="Здравствуйте, вы в AvtoBot'e!",
                reply_markup=get_callback_btns(
                    btns={
                        BUTTONS["Profile"]: "profile",
                        BUTTONS["Reminders"]: "reminders",
                        BUTTONS["Notes"]: "notes",
                        BUTTONS["Good_purchases"]: "good_purchases",
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
        cars = await rq.get_cars(tg_id=event.from_user.id)

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
        btns = {f"{i}": f'remove_auto:{car.car_id}' for i, car in enumerate(cars, start=1)}
        await callback.message.edit_text(
            text=text,
            reply_markup=get_callback_btns(
                btns={**btns, **{"⬅️ Назад": "back"}},
                custom=True
            )
        )

    @on.callback_query(F.data.regexp(r'remove_auto:(\d+)'))
    async def _remove_auto(self, callback: types.CallbackQuery, state: FSMContext):
        """
        Удаление выбранного автомобиля.
        """
        car_id = callback.data.split(":")[1]
        await rq.remove_car(car_id=car_id)
        await callback.message.answer("Автомобиль успешно удалён!")
        await callback.message.bot.delete_messages(
            chat_id=callback.message.chat.id,
            message_ids=[callback.message.message_id + 1]
        )
        await self.wizard.retake()

@user_private.message(AddCar.name, F.text.regexp(r'^\w+$'))
async def add_auto_name(message: types.Message, state: FSMContext):
    """
    Сохранение названия автомобиля и переход к вводу года.
    """
    existing_car = await rq.get_cars(message.from_user.id)
    if not any(car.name.lower() == message.text.lower() for car in existing_car):
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
    if 1900 < int(message.text) <= 2024:
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
@user_private.message(AddCar.year)
async def incorrect_auto_year(message: types.Message):
    """
    Обработка некорректного ввода года автомобиля.
    """
    await message.answer(text="Введите параметры настоящего автомобиля.")

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
    description = State()

class Purchase(Scene, state='purchases'):
    """
    Сцена управления заметками пользователя.
    """
    @on.message.enter()
