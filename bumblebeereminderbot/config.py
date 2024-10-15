import os
from dotenv import load_dotenv, find_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv(find_dotenv())

# Получение токена бота из переменных окружения
TOKEN = os.environ["TOKEN"]
