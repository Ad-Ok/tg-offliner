from telethon.sync import TelegramClient
from config import API_ID, API_HASH, PHONE

def connect_to_telegram():
    client = TelegramClient('session_name', API_ID, API_HASH)
    client.start(PHONE)

    if not client.is_user_authorized():
        client.send_code_request(PHONE)
        client.sign_in(PHONE, input('Введите код из Telegram: '))

    return client