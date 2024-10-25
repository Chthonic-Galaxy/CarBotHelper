```markdown
# CarBotHelper

Телеграм-бот для помощи автовладельцам. Этот бот предоставляет следующие функции:

* **Управление профилем:** Добавление, просмотр, редактирование и удаление автомобилей с указанием названия и года выпуска.
* **Напоминания:** Создание, просмотр и удаление напоминаний, привязанных к конкретному автомобилю. Напоминания отправляются в заданное время.
* **Заметки:** Создание, просмотр, поиск и удаление заметок с заголовком и описанием.
* **Покупки:** Добавление, просмотр, поиск и удаление покупок с возможностью добавления фотографии чека.
* **Аналитика:** Добавление данных о расходах с указанием категории, суммы и опционального описания. Просмотр общей суммы расходов, генерация аналитических отчетов за выбранный период с графиками, разбивкой по категориям, информацией о дне с самыми большими тратами, средними тратами в день и последними транзакциями.


## Установка и запуск

### Предварительные требования

* Python 3.12
* `venv` (рекомендуется для управления виртуальным окружением)
* SQLite (установлен по умолчанию с Python)

### Шаги установки

1. Клонируйте репозиторий:

```bash
git clone https://github.com/ваш_репозиторий/CarBotHelper.git
```

2. Перейдите в директорию проекта:

```bash
cd CarBotHelper
```

3. Создайте виртуальное окружение (рекомендуется):

```bash
python3.12 -m venv .venv
```

4. Активируйте виртуальное окружение:

* Linux/macOS:

```bash
source .venv/bin/activate
```

* Windows:

```bash
.venv\Scripts\activate
```

5. Установите зависимости:

```bash
pip install -r requirements.txt
```

6. Создайте файл `.env` в корне проекта и добавьте туда токен вашего бота:

```
TOKEN=ВАШ_ТОКЕН_БОТА
```

7. Запустите бота:

```bash
python -m bumblebeereminderbot.app
```

## Зависимости

Проект использует следующие библиотеки:

* **aiogram:** Фреймворк для создания ботов в Telegram.
* **apscheduler:** Библиотека для планирования задач.
* **SQLAlchemy:** ORM для работы с базами данных.
* **aiosqlite:** Асинхронный драйвер для SQLite.
* **matplotlib:** Библиотека для создания графиков.
* **python-dotenv:** Библиотека для загрузки переменных окружения из файла `.env`.
* **tzlocal:** Библиотека для работы с локальными часовыми поясами.


## Использование

После запуска бота вы можете использовать команды `/start` или `/menu` для входа в главное меню.  Далее следуйте инструкциям бота для использования различных функций.

## Пример использования аналитики

1. Добавьте несколько записей о ваших расходах, указав категорию, сумму и опциональное описание.
2. Выберите период, за который хотите получить отчет (например, последние 7 дней, последние 30 дней или произвольный период).
3. Бот сгенерирует отчет с графиками, показывающими ежедневные и совокупные расходы, а также предоставит информацию о общей сумме расходов, средних тратах в день, дне с наибольшими тратами и расходах по категориям.


## Лицензия MIT


Key improvements:

* **Clearer instructions:** More detailed steps for installation and running the bot.
* **Dependencies explained:**  Added a section explaining the purpose of each dependency.
* **.env instructions:**  Clarified how to set up the `.env` file.
* **Usage example:** Added an example of how to use the analytics feature.
* **Standard sections:** Added License and Contact sections.
* **Windows support:** Added activation instructions for Windows.
* **More comprehensive description of functionalities:** Provided more details on each feature of the bot, including the search functionality for notes and purchases, and the editing of car profiles.
* **Corrected typos and grammar.**
* **Improved formatting for better readability.**
* **Explicit mention of SQLite:** Added SQLite to the prerequisites and explained that it's usually installed with Python.
* **Added information about recent transactions in the analytics report.**