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
    "include_discussion_comments": True,  # Импортировать комментарии из группы обсуждений
    "message_limit": None,  # None для безлимитного скачивания, либо число (для тестирования можно поставить 100)
    "comments_search_limit": 1000,  # Лимит поиска сообщений в группе обсуждений
    "comments_forward_search_limit": 500  # Лимит поиска форвардированных постов
}