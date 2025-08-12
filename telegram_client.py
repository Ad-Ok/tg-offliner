from telethon.sync import TelegramClient
from config import API_ID, API_HASH, PHONE
import asyncio
import threading
import time
import os

# Глобальный клиент для переиспользования
_global_client = None
_client_lock = threading.Lock()
_client_loop = None  # Запоминаем event loop клиента

def connect_to_telegram():
    global _global_client, _client_loop
    
    # Проверяем, есть ли уже event loop в текущем потоке
    try:
        current_loop = asyncio.get_event_loop()
    except RuntimeError:
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)
    
    # Используем блокировку для безопасной работы с глобальным клиентом
    with _client_lock:
        # Если клиент не создан или event loop изменился - создаем новый
        if (_global_client is None or 
            not _global_client.is_connected() or 
            _client_loop != current_loop):
            
            # Отключаем старый клиент если есть
            if _global_client and _global_client.is_connected():
                try:
                    _global_client.disconnect()
                except:
                    pass
            
            # Создаем новый клиент с текущим event loop
            _global_client = TelegramClient('session_name', API_ID, API_HASH)
            _global_client.start(PHONE)
            _client_loop = current_loop  # Запоминаем event loop

            if not _global_client.is_user_authorized():
                raise Exception("Telegram клиент не авторизован. Запустите скрипт в интерактивном режиме для первоначальной авторизации.")

    return _global_client

def disconnect_global_client():
    """Отключает глобальный клиент"""
    global _global_client, _client_loop
    with _client_lock:
        if _global_client and _global_client.is_connected():
            _global_client.disconnect()
            _global_client = None
            _client_loop = None