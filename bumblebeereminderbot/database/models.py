from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Float, Integer, Boolean
from sqlalchemy.dialects.sqlite import DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

# Создание асинхронного двигателя для подключения к базе данных SQLite с использованием aiosqlite
engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3')

# Создание асинхронного sessionmaker для управления сессиями с базой данных
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    """
    Базовый класс для всех моделей ORM, использующий асинхронные атрибуты.
    """
    pass


class User(Base):
    """
    Модель пользователей, представляющая таблицу 'users' в базе данных.
    """
    __tablename__ = "users"  # Название таблицы в базе данных

    # Первичный ключ таблицы и уникальный идентификатор пользователя в Telegram
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)


class Car(Base):
    """
    Модель машин, представляющая таблицу 'cars' в базе данных.
    """
    __tablename__ = "cars"  # Название таблицы в базе данных

    # Первичный ключ таблицы
    car_id: Mapped[int] = mapped_column(primary_key=True)
    # Название автомобиля
    name: Mapped[str] = mapped_column(String(50))
    # Год выпуска автомобиля
    year: Mapped[str] = mapped_column(String(30))
    
    # Внешний ключ, связывающий событие с пользователем
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    # Определение отношения между Car и User моделями
    tg = relationship("User", foreign_keys=[tg_id], cascade="all, delete")


class Reminder(Base):
    """
    Модель напоминаний, представляюшая таблицу 'reminders' в базе данных.
    """
    __tablename__ = "reminders" # Название таблицы в базе данных

    # Первичный ключ таблицы
    reminder_id: Mapped[int] = mapped_column(primary_key=True)
    # Название напоминания
    reminder_title: Mapped[str] = mapped_column(String(64))
    # Описание напоминания
    reminder_description: Mapped[str] = mapped_column(String(256), nullable=True, default='Напоминание')
    # Дата и время когда следует напомнить
    reminder_date: Mapped[DateTime] = mapped_column(DateTime)
    # Отметка о выполнении напоминания
    is_done_reminder: Mapped[bool] = mapped_column(Boolean, default=False)

    # Внешний ключ, связывающий событие с автомобилем
    car_id = mapped_column(Integer, ForeignKey("cars.car_id"))
    # Определение отношения между Reminder и Car моделями
    car = relationship("Car", foreign_keys=[car_id], cascade="all, delete")


class Note(Base):
    """
    Модель заметок, представляет таблицу 'notes' в базе данных
    """
    __tablename__ = "notes" # Название таблицы в базе данных

    # Первичный ключ таблицы
    note_id: Mapped[int] = mapped_column(primary_key=True)
    # Название заметки
    note_title: Mapped[str] = mapped_column(String(64))
    # Описание заметки
    note_description: Mapped[str] = mapped_column(String(256), nullable=True, default='Заметка')
    # Дата создания заметки
    note_date: Mapped[DateTime] = mapped_column(DateTime)

    # Внешний ключ, связывающий заметку с пользователем
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    # Определение отношения между Note и User моделями
    tg = relationship("User", foreign_keys=[tg_id], cascade="all, delete")


class Purchase(Base):
    """
    Модель покупок, представляет таблицу 'purchases' в базе данных
    """
    __tablename__ = "purchases" # Название таблицы в базе данных

    # Первичный ключ таблицы
    purchase_id: Mapped[int] = mapped_column(primary_key=True)
    # Название покупки 
    purchase_title: Mapped[str] = mapped_column(String(64))
    # Фото покупки
    purchase_photo: Mapped[str] = mapped_column(String, nullable=True)
    # Дата покупки
    purchase_date: Mapped[DateTime] = mapped_column(DateTime)

    # Внешний ключ, связывающий покупку с пользователем
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    # Определение отношения между Purchase и User моделями
    tg = relationship("User", foreign_keys=[tg_id], cascade="all, delete")


class Analytics(Base):
    """
    Модель аналитики, представляет таблицу 'analytics' в базе данных
    """
    __tablename__ = "analytics" # Название таблицы в базе данных

    # Первичный ключ таблицы
    analytics_id: Mapped[int] = mapped_column(primary_key=True)
    # Название покупки
    analytics_title: Mapped[str] = mapped_column(String(64))
    # Описание покупки
    analytics_description: Mapped[str] = mapped_column(String(256), nullable=True, default="Аналитика")
    # Дата покупки
    analytics_date: Mapped[DateTime] = mapped_column(DateTime)
    # Стоимость покупки
    analytics_price: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)

    # Внешний ключ, связывающий аналитику с пользователем
    tg_id = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    # Определение отношения между Analytics и User моделями
    tg = relationship("User", foreign_keys=[tg_id], cascade="all, delete")


async def async_main():
    """
    Асинхронная функция для создания всех таблиц в базе данных на основе определенных моделей.
    """
    async with engine.begin() as conn:
        # Создание всех таблиц, если они еще не существуют
        await conn.run_sync(Base.metadata.create_all)
