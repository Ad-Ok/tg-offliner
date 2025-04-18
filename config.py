from dotenv import load_dotenv
import os

# Загружаем переменные из .env
load_dotenv()

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "telegram_export")
DOWNLOADS_DIR = "downloads"

EXPORT_SETTINGS = {
    "include_system_messages": False,
    "include_reposts": True,
    "include_polls": True,
    "message_limit": 20  # False для безлимитного скачивания, либо число
}