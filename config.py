from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
CHAT_USERNAME = os.getenv("CHAT_USERNAME")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "telegram_export")