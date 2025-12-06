#!/usr/bin/env python3
"""
Simplified authorization check that only verifies the session file exists.
Does not attempt to connect to Telegram to avoid startup delays.
"""

import os
import sys
from config import API_ID, API_HASH, PHONE

def check_and_authorize():
    """Checks if session file exists without connecting to Telegram."""
    print("🔍 Проверка авторизации в Telegram...")
    
    # Check environment variables
    if not API_ID or not API_HASH or not PHONE:
        print("❌ Ошибка: Не заданы API_ID, API_HASH или PHONE в .env файле")
        print("📝 Создайте файл .env на основе example.env и заполните его данными")
        return False
    
    print(f"📱 Номер телефона: {PHONE}")
    
    # Check if session file exists
    session_file = 'session_name.session'
    
    if os.path.exists(session_file) and os.path.getsize(session_file) > 0:
        print("✅ Файл сессии найден!")
        print(f"�� Размер: {os.path.getsize(session_file)} байт")
        return True
    else:
        print("❌ Файл сессии не найден или пуст")
        print("📞 Требуется авторизация...")
        print("\n🔐 ТРЕБУЕТСЯ АВТОРИЗАЦИЯ В TELEGRAM:")
        print("1. Остановите контейнер (Ctrl+C)")
        print("2. Запустите: docker compose run --rm app python authorize_telegram.py")
        print("3. Введите код из Telegram")
        print("4. Перезапустите контейнер: docker compose up")
        return False

def main():
    """Основная функция проверки авторизации."""
    print("=" * 50)
    print("🚀 Запуск приложения Telegram Offliner")
    print("=" * 50)
    
    # Проверяем авторизацию
    if check_and_authorize():
        print("✅ Авторизация успешна! Запуск веб-сервера...")
        return True
    else:
        print("❌ Авторизация не выполнена. Приложение не может работать без неё.")
        return False

if __name__ == "__main__":
    if not main():
        sys.exit(1)
