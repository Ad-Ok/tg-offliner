#!/usr/bin/env python3
"""
Скрипт для первоначальной авторизации в Telegram.
Запустите этот скрипт один раз для авторизации, после чего веб-сервер сможет использовать сессию.

Использование:
  В Docker: docker compose run --rm app python authorize_telegram.py
  На хосте: python authorize_telegram.py
"""

from telethon.sync import TelegramClient
from config import API_ID, API_HASH, PHONE
import sys

def authorize():
    print("=" * 60)
    print("🔐 АВТОРИЗАЦИЯ В TELEGRAM")
    print("=" * 60)
    
    # Проверяем наличие переменных окружения
    if not API_ID or not API_HASH or not PHONE:
        print("❌ Ошибка: Не заданы API_ID, API_HASH или PHONE в .env файле")
        print("📝 Создайте файл .env на основе example.env и заполните его данными")
        return False
        
    print(f"📱 Номер телефона: {PHONE}")
    
    # Создаем клиент с той же сессией, что использует веб-сервер
    client = TelegramClient('session_name', API_ID, API_HASH)
    
    try:
        print("🔄 Подключение к Telegram...")
        client.start(PHONE)
        
        if client.is_user_authorized():
            print("✅ Авторизация успешна!")
            print("🎉 Теперь веб-сервер может использовать Telegram API.")
            
            # Тестируем подключение
            me = client.get_me()
            print(f"👤 Авторизован как: {me.first_name} {me.last_name or ''}")
            if me.username:
                print(f"📧 Username: @{me.username}")
            
            print("\n✅ Готово! Теперь можно запустить приложение:")
            print("   docker compose up")
            
            return True
        else:
            print("❌ Ошибка авторизации")
            return False
            
    except KeyboardInterrupt:
        print("\n❌ Авторизация прервана пользователем")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        try:
            client.disconnect()
            print("📴 Отключение от Telegram")
        except:
            pass

if __name__ == "__main__":
    success = authorize()
    if not success:
        sys.exit(1)
