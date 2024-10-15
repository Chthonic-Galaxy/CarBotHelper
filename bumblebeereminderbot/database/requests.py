from .models import async_session
from .models import User, Car, Reminder, Note, Purchase, Analytics
from sqlalchemy import select



async def set_user(tg_id):
    """
    Асинхронная функция для добавления пользователя в базу данных, если он еще не существует
    
    :param tg_id: ID пользователя в Telegram
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск пользователя по его tg_id
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

        # Если пользователь не найден, добавляем его в базу данных
        if not user:
            session.add(User(tg_id=tg_id))
            # Фиксация изменений в базе данных
            await session.commit()

async def set_car(name, year, tg_id):
    """
    Асинхронная функция для добавления автомобиля в базу данных, если автомобиль еще не существует
    :param name: Название автомобиля
    :param year: Год выпуска автомобиля
    :param tg_id: Внешний ключ между Car и User
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получаем список автомобилей пользователя с указанным tg_id
        result = await session.scalars(select(Car).where(Car.tg_id == tg_id))
        
        # Проверяем, существует ли автомобиль с таким же именем
        if not any(name == car.name for car in result):
            # Если автомобиля нет, добавляем его
            session.add(Car(name=name, year=year, tg_id=tg_id))
            # Фиксация изменений в базе данных
            await session.commit()
        else:
            # Если автомобиль уже существует, выбрасываем ошибку
            raise ValueError("Такой автомобиль уже существует.")

async def set_reminder(reminder_title, reminder_date, car_id, reminder_description=None):
    """
    Асинхронная функция для добавления напоминания в базу данных, если напоминание еще не существует
    :param reminder_title: Название напоминания
    :param reminder_description: Описание напоминания, опционально
    :param reminder_date: Дата и время когда следует напомнить
    :param car_id: Внешний ключ, между Reminder и Car моделями
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск названия автомобиля по его car_id через связь между Reminder и Car
        car = session.scalar(select(Reminder).where(Reminder.car_id == car_id))
        # Поиск названия напоминания по его reminder_title
        title = session.scalar(select(Reminder).where(Reminder.reminder_title == reminder_title))

        # Если у автомобиля, напоминание не найдено, добавляем его в базу данных
        if car and not title:
            session.add(Reminder(
                reminder_title=reminder_title,
                reminder_description=reminder_description,
                reminder_date=reminder_date, car_id=car_id
                )
            )
            # Фиксация изменений в базе данных
            session.commit()

async def set_note(note_title, note_date, tg_id, note_description=None):
    """
    Асинхронная функция для добавления заметок в базу данных, если заметки еще не существует
    :param note_title: Название заметки
    :param note_description: Описание заметки, опционально
    :param note_date: Дата и время создания заметки
    :param tg_id: Внешний ключ, между Note и User моделями
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск пользователя по его tg_id через связь между Note и User
        user = session.scalar(select(Note).where(Note.tg_id == tg_id))
        # Поиск названия заметки по её note_title
        title = session.scalar(select(Note).where(Note.note_title == note_title))

        # Если у пользователя, заметка не найдена, добавляем её в базу данных
        if user and not title:
            session.add(Note(
                note_title=note_title,
                note_description=note_description,
                note_date=note_date,
                tg_id=tg_id
            )
        )
            # Фиксация изменений в базе данных
            session.commit()

async def set_purchase(purchase_date, tg_id, purchase_title=None, purchase_photo=None):
    """
    Асинхронная функция для добавления покупки в базу данных
    :param purchase_title: Название покупки, опционально
    :param purchase_photo: Фото покупки, опционально
    :param purchase_date: Дата и время покупки
    :param tg_id: Внешний ключ, между Purchase и User моделями
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Добавление покупки в базу данных
        session.add(Purchase(
            purchase_title=purchase_title,
            purchase_photo=purchase_photo,
            purchase_date=purchase_date,
            tg_id=tg_id
            )
        )
        # Фиксация асинхронной сессии с базой данных
        session.commit()

async def set_analytics(
        analytics_title,
        analytics_date,
        analytics_price,
        tg_id,
        analytics_description=None
    ):
    """
    Асинхронная функция для добавления лучших покупок в базу данных, если покупка отсутствует
    :param analytics_title: Название покупки
    :param analytics_description: Описание покупки, опционально
    :param analytics_date: Дата и время покупки
    :param tg_id: Внешний ключ, между Purchase и User моделями
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск пользователя по его tg_id через связь между Analytics и User
        user = session.scalar(select(Analytics).where(Analytics.tg_id == tg_id))
        # Поиск названия покупки по её analytics_title
        title = session.scalar(select(Analytics).where(Analytics.analytics_title == analytics_title))

        # Если у пользователя, покупка не найдена, добавляем её в базу данных
        if user and not title:
            session.add(Analytics(
                analytics_title=analytics_title,
                analytics_description=analytics_description,
                analytics_date=analytics_date,
                analytics_price=analytics_price,
                tg_id=tg_id
            )
        )
            # Фиксация асинхронной сессии с базой данных
            session.commit()

async def get_cars(tg_id):
    """
    Асинхронная функция для получения всех автомобилей пользователя

    :param tg_id: Внешний ключ, между Car и User моделями
    :return: Генератор объектов Car, связанных с пользователем
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получение всех автомобилей пользователя по его tg_id
        return await session.scalars(select(Car).where(Car.tg_id == tg_id))

async def get_reminders(car_id):
    """
    Асинхронная функция для получения всех напоминаний

    :param car_id: Внешний ключ, между Reminder и Car моделями
    :return: Генератор объектов Reminder, связанных с автомобилем
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получение всех напоминаний по car_id
        await session.scalars(select(Reminder).where(Reminder.car_id == car_id))

async def get_notes(tg_id):
    """
    Асинхронная функция для получения всех заметок

    :param tg_id: Внешний ключ, между Note и User моделями
    :return: Генератор объектов Note, связанных с пользователем
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получение всех заметок по tg_id
        await session.scalars(select(Note).where(Note.tg_id == tg_id))

async def get_purchases(tg_id):
    """
    Асинхронная функция для получения всех покупок

    :param tg_id: Внешний ключ, между Purchase и User моделями
    :return: Генератор объектов Purchase, связанных с пользователем
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получение всех заметок по tg_id
        await session.scalars(select(Purchase).where(Purchase.tg_id == tg_id))

async def get_analytics(tg_id):
    """
    Асинхронная функция для получения всех отличных покупок и услуг

    :param tg_id: Внешний ключ, между Analytics и User моделями
    :return: Генератор объектов Analytics, связанных с пользователем
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Получение всех заметок по tg_id
        await session.scalars(select(Analytics).where(Analytics.tg_id == tg_id))

async def remove_car(car_id):
    """
    Асинхронная функция для удаления автомобиля из базы данных по его car_id.

    :param car_id: Уникальный идентификатор автомобиля.
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск автомобиля по его car_id
        car = await session.scalar(select(Car).where(Car.car_id == car_id))
    
        # Если автомобиль найден, удаляем его из базы данных
        if car:
            await session.delete(car)
            # Фиксация изменений в базе данных
            await session.commit()

async def remove_reminder(reminder_id):
    """
    Асинхронная функция для удаления напоминания из базы данных по его reminder_id.

    :param reminder_id: Уникальный идентификатор напоминания.
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск напоминания по его reminder_id
        id = await session.scalar(select(Reminder).where(Reminder.reminder_id == reminder_id))
    
        # Если напоминание найдено, удаляем его из базы данных
        if id:
            await session.delete(id)
            # Фиксация изменений в базе данных
            await session.commit()

async def remove_note(note_id):
    """
    Асинхронная функция для удаления напоминания из базы данных по его note_id.

    :param note_id: Уникальный идентификатор напоминания.
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск заметки по её note_id
        id = await session.scalar(select(Note).where(Note.note_id == note_id))
    
        # Если заметка найдена, удаляем её из базы данных
        if id:
            await session.delete(id)
            # Фиксация изменений в базе данных
            await session.commit()

async def remove_purchase(purchase_id):
    """
    Асинхронная функция для удаления покупки из базы данных по её purchase_id.

    :param purchase_id: Уникальный идентификатор покупки
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск покупки по её purchase_id
        id = await session.scalar(select(Purchase).where(Purchase.purchase_id == purchase_id))
    
        # Если покупка найдена, удаляем её из базы данных
        if id:
            await session.delete(id)
            # Фиксация изменений в базе данных
            await session.commit()

async def remove_analytics(analytics_id):
    """
    Асинхронная функция для удаления покупки из базы данных по её analytics_id

    :param analytics_id: Уникальный идентификатор покупки
    """
    # Создание асинхронной сессии с базой данных
    async with async_session() as session:
        # Поиск покупки по её analytics_id
        id = await session.scalar(select(Analytics).where(Analytics.analytics_id == analytics_id))
    
        # Если покупка найдена, удаляем её из базы данных
        if id:
            await session.delete(id)
            # Фиксация изменений в базе данных
            await session.commit()
