from telethon.sync import TelegramClient
from config import EXPORT_SETTINGS
from telegram_client import connect_to_telegram
import time
import argparse
import requests
from utils.text_format import parse_entities_to_html
import os
from message_processing.polls import process_poll
from telethon.tl.types import DocumentAttributeFilename, Document, MessageMediaDocument, MessageMediaWebPage, DocumentAttributeSticker
from message_processing.author import process_author, download_avatar
import shutil
import os
import logging
from message_processing.channel_info import get_channel_info
from utils.entity_validation import get_entity_by_username_or_id

# Настройка логирования
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

def should_stop_import(channel_id):
    """Проверяет, нужно ли остановить импорт"""
    if not channel_id:
        return False
    
    try:
        # Импортируем функцию проверки из app.py
        import requests
        response = requests.get(f"http://localhost:5000/api/download/status/{channel_id}")
        if response.status_code == 200:
            status_data = response.json()
            return status_data.get('status') == 'stopped'
    except Exception as e:
        logging.warning(f"Не удалось проверить статус остановки: {e}")
    
    return False

def update_import_progress(channel_id, processed_posts, processed_comments, total_posts=None):
    """Обновляет прогресс импорта"""
    if not channel_id:
        return
    
    try:
        import requests
        data = {
            'posts_processed': processed_posts,
            'comments_processed': processed_comments
        }
        if total_posts is not None:
            data['total_posts'] = total_posts
            
        requests.post(f"http://localhost:5000/api/download/progress/{channel_id}", 
                     json=data, timeout=5)
    except Exception as e:
        logging.warning(f"Не удалось обновить прогресс: {e}")
        # Здесь можно добавить API для обновления прогресса, пока просто логируем
        logging.info(f"Прогресс импорта {channel_id}: {processed_posts} постов, {processed_comments} комментариев")
    except Exception as e:
        logging.warning(f"Не удалось обновить прогресс: {e}")

def import_channel_direct(channel_username, channel_id=None):
    """
    Импортирует канал или переписку с пользователем напрямую, используя существующий клиент.
    Возвращает словарь с результатом.
    
    :param channel_username: Имя канала или пользователя
    :param channel_id: ID канала для отслеживания статуса (опционально)
    """
    try:
        # Используем существующий глобальный клиент
        client = connect_to_telegram()
        
        # Получаем entity по username или ID
        from utils.entity_validation import get_entity_by_username_or_id, validate_entity_for_download
        entity, error_message = get_entity_by_username_or_id(client, channel_username)
        
        if entity is None:
            return {"success": False, "error": error_message}
        
        # Проверяем, что это публичный канал или пользователь
        validation_result = validate_entity_for_download(entity, channel_username)
        
        if not validation_result["valid"]:
            return {"success": False, "error": validation_result["error"]}
        
        # Определяем реальный ID для базы данных и безопасное имя папки
        real_id = entity.username or str(entity.id)
        # Для папки используем префикс, чтобы избежать конфликтов с числовыми ID
        folder_name = entity.username or f"user_{entity.id}" if hasattr(entity, 'first_name') else entity.username or f"channel_{entity.id}"
        
        logging.info(f"Реальный ID для {channel_username}: {real_id}")
        logging.info(f"Имя папки: {folder_name}")
        
        # Очищаем папку канала по имени папки
        clear_downloads(folder_name)
        
        # Сохраняем информацию о канале в базу
        channel_info = get_channel_info(client, entity, output_dir="downloads", folder_name=folder_name)
        logging.info(f"Информация о канале: {channel_info}")
        
        # Добавляем канал в базу данных через API
        api_url = "http://localhost:5000/api/channels"
        response = requests.post(api_url, json=channel_info)
        
        if response.status_code not in [200, 201]:
            logging.error(f"Ошибка добавления канала в БД: {response.text}")
            return {"success": False, "error": f"Ошибка БД: {response.text}"}
        
        # Импортируем сообщения
        include_system_messages = EXPORT_SETTINGS.get("include_system_messages", False)
        include_reposts = EXPORT_SETTINGS.get("include_reposts", True)
        include_polls = EXPORT_SETTINGS.get("include_polls", True)
        include_discussion_comments = EXPORT_SETTINGS.get("include_discussion_comments", True)
        message_limit = EXPORT_SETTINGS.get("message_limit", None)

        all_posts = client.iter_messages(
            entity,
            limit=message_limit,
            reverse=True
        )
        
        # Получаем общее количество сообщений для прогресса
        total_posts = 0
        if message_limit:
            total_posts = min(message_limit, entity.count if hasattr(entity, 'count') else message_limit)
        else:
            total_posts = entity.count if hasattr(entity, 'count') else 0
        
        processed_count = 0
        comments_count = 0
        
        # Получаем ID группы обсуждений для импорта комментариев
        discussion_group_id = channel_info.get('discussion_group_id')
        
        # Инициализируем прогресс
        update_import_progress(channel_id, 0, 0, total_posts)
        
        for post in all_posts:
            try:
                # Проверяем, нужно ли остановить импорт
                if should_stop_import(channel_id):
                    logging.info(f"Импорт канала {channel_username} остановлен пользователем")
                    return {"success": True, "processed": processed_count, "comments": comments_count, "stopped": True}
                
                # Пропускаем системные сообщения, если они отключены
                if not include_system_messages and post.action:
                    logging.info(f"Пропущено системное сообщение с ID {post.id}")
                    continue

                # Пропускаем репосты, если они отключены
                if not include_reposts and post.fwd_from:
                    logging.info(f"Пропущен репост с ID {post.id}")
                    continue

                # Пропускаем опросы, если они отключены
                if not include_polls and post.poll:
                    logging.info(f"Пропущен опрос с ID {post.id}")
                    continue
                
                # Обрабатываем сообщение так же, как в main()
                post_data = process_message_for_api(post, real_id, client, folder_name)
                if post_data:
                    # Добавляем пост через API
                    api_url = "http://localhost:5000/api/posts"
                    response = requests.post(api_url, json=post_data)
                    if response.status_code in [200, 201]:
                        processed_count += 1
                        
                        # Если у канала есть группа обсуждений и включен импорт комментариев
                        if discussion_group_id and include_discussion_comments:
                            post_comments = import_discussion_comments(
                                client, 
                                real_id, 
                                discussion_group_id, 
                                post.id
                            )
                            comments_count += post_comments
                    else:
                        logging.error(f"Ошибка добавления поста {post.id}: {response.text}")
                
                # Обновляем прогресс каждые 5 постов или на каждом посте, если постов мало
                if processed_count % 5 == 0 or total_posts < 50:
                    update_import_progress(channel_id, processed_count, comments_count, total_posts)
                        
            except Exception as e:
                logging.error(f"Ошибка при обработке сообщения: {str(e)}")
        
        logging.info(f"Обработано сообщений: {processed_count}")
        logging.info(f"Импортировано комментариев: {comments_count}")
        logging.info(f"Канал {channel_username} импортирован: {processed_count} сообщений, {comments_count} комментариев")
        
        # Финальное обновление прогресса
        update_import_progress(channel_id, processed_count, comments_count, total_posts)
        
        return {"success": True, "processed": processed_count, "comments": comments_count}
        
    except Exception as e:
        logging.error(f"Ошибка импорта канала {channel_username}: {str(e)}")
        return {"success": False, "error": str(e)}

def import_discussion_comments(client, channel_id, discussion_group_id, original_post_id):
    """
    Импортирует комментарии к посту из группы обсуждений канала.
    
    :param client: Подключённый клиент Telethon
    :param channel_id: ID канала (для связи комментариев)
    :param discussion_group_id: ID группы обсуждений
    :param original_post_id: ID оригинального поста в канале
    :return: Количество импортированных комментариев
    """
    try:
        logging.info(f"Поиск комментариев к посту {original_post_id} в группе обсуждений {discussion_group_id}")
        
        # Получаем entity группы обсуждений
        discussion_entity, error = get_entity_by_username_or_id(client, str(discussion_group_id))
        if discussion_entity is None:
            logging.error(f"Не удалось получить группу обсуждений {discussion_group_id}: {error}")
            return 0

        # Сохраняем информацию о дискуссионной группе в таблицу channels
        logging.info(f"Сохраняем информацию о дискуссионной группе {discussion_group_id}")
        try:
            save_discussion_group_info(client, discussion_entity)
        except Exception as e:
            logging.error(f"Ошибка сохранения дискуссионной группы {discussion_group_id}: {e}")
        
        # Создаем папку для комментариев (используем тот же формат, что и для канала)
        folder_name = f"discussion_{discussion_group_id}"
        
        # Сначала ищем форвардированный пост в группе обсуждений
        forwarded_post_id = None
        comments_count = 0
        
        try:
            # Получаем настройки из конфигурации
            forward_search_limit = EXPORT_SETTINGS.get("comments_forward_search_limit", 500)
            comments_search_limit = EXPORT_SETTINGS.get("comments_search_limit", 1000)
            
            # Ищем среди последних сообщений форвардированный пост из канала
            recent_messages = client.iter_messages(discussion_entity, limit=forward_search_limit)
            
            for message in recent_messages:
                # Проверяем, является ли сообщение форвардом из нашего канала
                if (hasattr(message, 'fwd_from') and 
                    message.fwd_from and 
                    hasattr(message.fwd_from, 'from_id')):
                    
                    # Дополнительно проверяем по saved_from_msg_id если доступно
                    if (hasattr(message.fwd_from, 'saved_from_msg_id') and 
                        message.fwd_from.saved_from_msg_id == original_post_id):
                        forwarded_post_id = message.id
                        logging.info(f"Найден форвардированный пост {forwarded_post_id} для оригинального поста {original_post_id}")
                        break
                    
                    # Альтернативный поиск: проверяем дату и содержимое
                    # Иногда saved_from_msg_id может отсутствовать
                    if hasattr(message.fwd_from, 'date'):
                        logging.debug(f"Проверяем форвард с датой {message.fwd_from.date}")
            
            # Если нашли форвардированный пост, ищем ответы на него
            if forwarded_post_id:
                all_messages = client.iter_messages(discussion_entity, limit=comments_search_limit)
                
                for message in all_messages:
                    try:
                        # Проверяем, является ли сообщение ответом на форвардированный пост
                        if (hasattr(message, 'reply_to') and 
                            message.reply_to and 
                            hasattr(message.reply_to, 'reply_to_msg_id') and
                            message.reply_to.reply_to_msg_id == forwarded_post_id):
                            
                            logging.info(f"Найден комментарий {message.id} к форвардированному посту {forwarded_post_id}")
                            
                            # Обрабатываем комментарий с discussion_group_id вместо channel_id
                            logging.info(f"Обрабатываем комментарий {message.id} с channel_id={discussion_group_id}")
                            comment_data = process_message_for_api(message, str(discussion_group_id), client, folder_name)
                            if comment_data:
                                # Устанавливаем правильную связь с оригинальным постом канала
                                comment_data['reply_to'] = original_post_id
                                logging.info(f"Данные комментария {message.id}: channel_id={comment_data.get('channel_id')}, reply_to={comment_data.get('reply_to')}")
                                
                                # Добавляем комментарий в базу данных
                                api_url = "http://localhost:5000/api/posts"
                                response = requests.post(api_url, json=comment_data)
                                if response.status_code in [200, 201]:
                                    comments_count += 1
                                    logging.info(f"Комментарий {message.id} успешно добавлен как ответ на пост {original_post_id}")
                                else:
                                    logging.error(f"Ошибка добавления комментария {message.id}: {response.text}")
                        
                    except Exception as e:
                        logging.error(f"Ошибка обработки сообщения {message.id} из группы обсуждений: {e}")
            else:
                logging.warning(f"Не найден форвардированный пост для оригинального поста {original_post_id} среди {forward_search_limit} последних сообщений")
                # Для отладки: попробуем найти любые форварды из канала
                debug_forwards_found = 0
                for message in client.iter_messages(discussion_entity, limit=100):
                    if (hasattr(message, 'fwd_from') and message.fwd_from):
                        debug_forwards_found += 1
                        if hasattr(message.fwd_from, 'saved_from_msg_id'):
                            logging.debug(f"Найден форвард с saved_from_msg_id: {message.fwd_from.saved_from_msg_id}")
                
                logging.info(f"Всего найдено форвардов в группе обсуждений: {debug_forwards_found}")
                    
        except Exception as e:
            logging.error(f"Ошибка получения сообщений из группы обсуждений: {e}")
            
        logging.info(f"Импортировано {comments_count} комментариев к посту {original_post_id}")
        return comments_count
        
    except Exception as e:
        logging.error(f"Ошибка импорта комментариев: {e}")
        return 0


def save_discussion_group_info(client, discussion_entity):
    """
    Сохраняет информацию о дискуссионной группе в таблицу channels.
    
    :param client: Подключённый клиент Telethon
    :param discussion_entity: Entity дискуссионной группы
    """
    try:
        discussion_info = get_channel_info(client, discussion_entity, output_dir="downloads")
        discussion_info["id"] = str(discussion_entity.id)
        
        # Добавляем метку, что это дискуссионная группа
        discussion_info["name"] = f"💬 {discussion_info['name']} (обсуждения)"
        
        # Убираем discussion_group_id, так как дискуссионная группа не должна ссылаться на другую группу
        discussion_info["discussion_group_id"] = None
        
        # Сохраняем в базу данных
        api_url = "http://localhost:5000/api/channels"
        response = requests.post(api_url, json=discussion_info)
        if response.status_code in [200, 201]:
            logging.info(f"Информация о дискуссионной группе {discussion_entity.id} сохранена")
        else:
            logging.warning(f"Не удалось сохранить информацию о дискуссионной группе {discussion_entity.id}: {response.text}")
    except Exception as e:
        logging.error(f"Ошибка сохранения информации о дискуссионной группе {discussion_entity.id}: {e}")


def process_message_for_api(post, channel_id, client, folder_name=None):
    """Обрабатывает сообщение для API"""
    try:
        # Получаем папку для канала
        if folder_name:
            channel_folder = get_channel_folder(folder_name)
        else:
            channel_folder = get_channel_folder(channel_id)
        
        # Скачиваем медиа
        media_path = None
        media_type = None
        mime_type = None
        sticker_emoji = None  # Для хранения эмодзи стикера

        if post.media and not post.poll:  # Пропускаем скачивание медиа для опросов
            media_type = type(post.media).__name__  # Тип медиа (например, MessageMediaPhoto)
            
            # Проверяем, является ли это TGS стикером
            if (isinstance(post.media, MessageMediaDocument) and 
                isinstance(post.media.document, Document) and 
                getattr(post.media.document, 'mime_type', None) == 'application/x-tgsticker'):
                
                # Для TGS стикеров ищем эмодзи в атрибутах
                for attr in post.media.document.attributes:
                    if isinstance(attr, DocumentAttributeSticker) and attr.alt:
                        sticker_emoji = attr.alt
                        logging.info(f"TGS sticker detected: will add emoji {attr.alt} to message text")
                        break
                
                # TGS стикеры не сохраняем как медиа - только эмодзи в тексте
                if sticker_emoji:
                    media_type = None  # Не сохраняем как медиа
                    mime_type = None
                    media_path = None
            
            # Обрабатываем MessageMediaWebPage
            elif isinstance(post.media, MessageMediaWebPage):
                # Для веб-страниц сохраняем URL страницы в media_url
                if hasattr(post.media, 'webpage') and post.media.webpage and hasattr(post.media.webpage, 'url'):
                    media_path = post.media.webpage.url
                    logging.info(f"MessageMediaWebPage detected: saving URL {media_path}")
            else:
                # Для остальных типов медиа скачиваем файлы
                media_path = client.download_media(
                    post.media,
                    file=os.path.join(channel_folder, "media", f"{post.id}_media")
                )
                # Сохраняем относительный путь для файлов
                if media_path:
                    media_path = os.path.relpath(media_path, DOWNLOADS_DIR)  # Относительный путь от папки downloads
            
            # Устанавливаем mime_type только если это не стикер
            if (isinstance(post.media, MessageMediaDocument) and 
                isinstance(post.media.document, Document) and 
                not sticker_emoji):  # Не устанавливаем mime_type для стикеров
                mime_type = getattr(post.media.document, 'mime_type', None)

        # Обрабатываем автора сообщения
        sender_name, sender_avatar, sender_link = process_author(post.sender, client, channel_folder, peer_id=post.peer_id, from_id=post.from_id)
        
        # Дополнительная обработка для анонимных комментариев из дискуссионных групп
        if not sender_name and hasattr(post, 'peer_id') and hasattr(post, 'reply_to'):
            # Если автор пустой и есть peer_id и reply_to, это может быть анонимный комментарий
            try:
                # Получаем информацию о группе/канале, где находится сообщение
                peer_entity = client.get_entity(post.peer_id)
                if hasattr(peer_entity, 'title'):  # Это группа или канал
                    sender_name = peer_entity.title
                    if hasattr(peer_entity, 'username') and peer_entity.username:
                        sender_link = f"https://t.me/{peer_entity.username}"
                    elif hasattr(peer_entity, 'id'):
                        sender_link = f"https://t.me/c/{peer_entity.id}"
                    
                    # Попытаемся скачать аватар группы/канала
                    sender_avatar = download_avatar(peer_entity, client, channel_folder)
                    logging.info(f"Использована информация о группе {sender_name} для анонимного комментария")
            except Exception as e:
                logging.warning(f"Ошибка при получении информации о peer для анонимного комментария: {e}")

        # Обрабатываем автора репоста, если это репост
        repost_name, repost_avatar, repost_link = None, None, None
        if post.fwd_from:
            # Случай 1: есть from_id (можем получить полную информацию)
            if post.fwd_from.from_id:
                try:
                    repost_entity = client.get_entity(post.fwd_from.from_id)  # Получаем полную информацию об авторе репоста
                    repost_name, repost_avatar, repost_link = process_author(repost_entity, client, channel_folder)
                except Exception as e:
                    logging.warning(f"Ошибка при обработке автора репоста: {e}")
            # Случай 2: есть только from_name (используем имя как есть)
            elif post.fwd_from.from_name:
                repost_name = post.fwd_from.from_name
                logging.info(f"Репост от пользователя: {repost_name} (только имя)")
            # Случай 3: есть channel_post (репост из канала)
            elif hasattr(post.fwd_from, 'saved_from_peer') and post.fwd_from.saved_from_peer:
                try:
                    channel_entity = client.get_entity(post.fwd_from.saved_from_peer)
                    repost_name = getattr(channel_entity, 'title', getattr(channel_entity, 'username', 'Unknown Channel'))
                    logging.info(f"Репост из канала: {repost_name}")
                except Exception as e:
                    logging.warning(f"Ошибка при обработке канала репоста: {e}")

        # Обрабатываем реакции
        reactions = None
        if post.reactions and post.reactions.results:
            reactions = {
                "total_count": sum(r.count for r in post.reactions.results),  # Суммируем количество всех реакций
                "recent_reactions": [
                    {"reaction": str(r.reaction), "count": r.count} for r in post.reactions.results
                ]
            }

        grouped_id = getattr(post, "grouped_id", None)
        print(f"process_message_for_api: post.id={getattr(post, 'id', None)} grouped_id={grouped_id}")

        # Обрабатываем информацию о том, является ли это ответом на другое сообщение
        reply_to = None
        if hasattr(post, 'reply_to') and post.reply_to and hasattr(post.reply_to, 'reply_to_msg_id'):
            reply_to = post.reply_to.reply_to_msg_id
            print(f"Сообщение {post.id} является ответом на сообщение {reply_to}")

        # Формируем текст сообщения
        message_text = post.message or ""
        
        # Обрабатываем системные сообщения
        if hasattr(post, 'action') and post.action:
            action_type = type(post.action).__name__
            
            if action_type == 'MessageActionChannelCreate':
                message_text = f"🎉 Канал создан: {post.action.title}"
            elif action_type == 'MessageActionChatEditPhoto':
                message_text = "🖼️ Фото канала изменено"
            elif action_type == 'MessageActionChatEditTitle':
                message_text = f"✏️ Название изменено на: {post.action.title}"
            elif action_type == 'MessageActionChatDeletePhoto':
                message_text = "🗑️ Фото канала удалено"
            elif action_type == 'MessageActionChatAddUser':
                message_text = "👥 Пользователь добавлен в группу"
            elif action_type == 'MessageActionChatDeleteUser':
                message_text = "👤❌ Пользователь покинул группу"
            elif action_type == 'MessageActionChatJoinedByLink':
                message_text = "🔗 Пользователь присоединился по ссылке"
            elif action_type == 'MessageActionPinMessage':
                message_text = "📌 Сообщение закреплено"
            elif action_type == 'MessageActionHistoryClear':
                message_text = "🧹 История сообщений очищена"
            elif 'PhoneCall' in action_type:
                # Обрабатываем звонки (оставляем существующую логику)
                call_action = post.action
                
                # Определяем направление звонка по from_id
                direction = "📤 Исходящий" if (hasattr(post, 'from_id') and post.from_id) else "📥 Входящий"
                
                # Определяем тип звонка
                video_type = "🎥 Видеозвонок" if getattr(call_action, 'video', False) else "📞 Голосовой звонок"
                
                # Определяем статус звонка
                reason = getattr(call_action, 'reason', None)
                if reason:
                    reason_type = type(reason).__name__
                    if 'Missed' in reason_type:
                        status = "🔴 Пропущен"
                    elif 'Busy' in reason_type:
                        status = "📵 Занято"
                    elif 'Hangup' in reason_type:
                        status = "✅ Завершен"
                    elif 'Disconnect' in reason_type:
                        status = "🔌 Разорвано"
                    else:
                        status = f"❓ {reason_type}"
                else:
                    status = "❓ Неизвестно"
                
                # Длительность
                duration = getattr(call_action, 'duration', None)
                if duration:
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_str = f"⏰ {minutes}м {seconds}с"
                else:
                    duration_str = "⏰ Не состоялся"
                
                # Формируем текст звонка
                message_text = f"{direction} {video_type} - {status} {duration_str}"
                logging.info(f"Phone call detected: {message_text}")
            else:
                # Для неизвестных типов системных сообщений
                message_text = f"ℹ️ Системное сообщение: {action_type}"
                logging.info(f"Unknown system message type: {action_type}")
        
        # Если есть эмодзи стикера, добавляем его к тексту
        elif sticker_emoji:
            if message_text:
                message_text = f"{message_text} {sticker_emoji}"
            else:
                message_text = sticker_emoji

        # Применяем форматирование к тексту, если есть entities
        if message_text and hasattr(post, 'entities') and post.entities:
            try:
                formatted_message = parse_entities_to_html(message_text, post.entities)
                # Если форматирование применилось успешно, используем отформатированный текст
                if formatted_message != message_text:
                    message_text = formatted_message
                    logging.info(f"Применено форматирование к сообщению {post.id}")
            except Exception as e:
                logging.warning(f"Ошибка применения форматирования к сообщению {post.id}: {e}")
                # В случае ошибки оставляем исходный текст

        return {
            "telegram_id": post.id,
            "channel_id": channel_id,
            "date": post.date.isoformat() if post.date else None,
            "message": message_text,
            "media_url": media_path,
            "media_type": media_type,
            "mime_type": mime_type,
            "author_name": sender_name,
            "author_avatar": sender_avatar,
            "author_link": sender_link,
            "repost_author_name": repost_name,
            "repost_author_avatar": repost_avatar,
            "repost_author_link": repost_link,
            "reactions": reactions,
            "grouped_id": grouped_id,
            "reply_to": reply_to
        }
    except Exception as e:
        logging.error(f"Ошибка обработки сообщения {post.id}: {str(e)}")
        return None

def clear_downloads(channel_name):
    """
    Очищает папку текущего канала в downloads, но не удаляет саму папку downloads.
    """
    channel_folder = os.path.join(DOWNLOADS_DIR, channel_name)
    if os.path.exists(channel_folder):
        shutil.rmtree(channel_folder)  # Удаляем папку канала со всем содержимым
        print(f"Папка {channel_folder} очищена.")
    os.makedirs(channel_folder, exist_ok=True)  # Создаём пустую папку

def get_channel_folder(channel_name):
    """
    Возвращает путь к папке для конкретного канала.
    """
    channel_folder = os.path.join(DOWNLOADS_DIR, channel_name)
    os.makedirs(channel_folder, exist_ok=True)  # Создаём папку канала, если её нет

    # Создаём папку media внутри папки канала
    media_folder = os.path.join(channel_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    return channel_folder

# def save_channel_info(client, channel_username):
#     print("== save_channel_info called ==")
#     try:
#         entity = client.get_entity(channel_username)
#         print("== entity получен ==")
#         channel_data = get_channel_info(client, entity, output_dir="downloads")
#         print("== channel_data:", channel_data)
#         channel_data["id"] = entity.username or str(entity.id)
#         print("== отправляем в API:", channel_data)
#         response = requests.post("http://127.0.0.1:5000/api/channels", json=channel_data)
#         print("== ответ API:", response.status_code, response.text)
#         if response.status_code == 201:
#             print(f"Канал {channel_data['name']} успешно добавлен в базу данных.")
#         elif response.status_code == 200:
#             print(f"Канал {channel_data['name']} уже существует.")
#         else:
#             print(f"Ошибка при добавлении канала: {response.text}")
#     except Exception as e:
#         print(f"Ошибка при сохранении информации о канале: {e}")

# def download_channel(channel_name):
#     logging.info(f"Начало скачивания канала: {channel_name}")
#     # Ваш код для скачивания
#     logging.info(f"Канал {channel_name} успешно скачан")

def main(channel_username=None):
    # Очищаем папку текущего канала
    clear_downloads(channel_username)

    start_time = time.time()

    # Подключение к Telegram
    client = connect_to_telegram()
    entity = client.get_entity(channel_username)

    # Сохраняем информацию о канале
    # save_channel_info(client, channel_username)  # временно отключено

    # Применяем параметры из EXPORT_SETTINGS
    include_system_messages = EXPORT_SETTINGS.get("include_system_messages", False)
    include_reposts = EXPORT_SETTINGS.get("include_reposts", True)
    include_polls = EXPORT_SETTINGS.get("include_polls", True)
    message_limit = EXPORT_SETTINGS.get("message_limit", None)

    # Получение списка сообщений
    all_posts = client.iter_messages(
        entity,
        limit=message_limit,
        reverse=True  # Обходим от старых к новым
    )
    processed_count = 0

    replace_all = None  # Флаг для "да для всех"

    for post in all_posts:
        # Пропускаем системные сообщения, если они отключены
        if not include_system_messages and post.action:
            print(f"Пропущено системное сообщение с ID {post.id}")
            continue

        # Пропускаем репосты, если они отключены
        if not include_reposts and post.fwd_from:
            continue

        # Пропускаем опросы, если они отключены
        if not include_polls and post.poll:
            continue

        # Проверяем, существует ли пост в базе
        try:
            response = requests.get(f"http://127.0.0.1:5000/api/posts/check?telegram_id={post.id}&channel_id={channel_username}")
            if response.status_code == 200:
                response_data = response.json()
                # Проверяем, что ответ содержит ключ "exists"
                if isinstance(response_data, dict) and response_data.get("exists"):
                    print(f"Пост с ID {post.id} из канала {channel_username} уже существует в базе.")
                    
                    # Если пользователь уже выбрал "да для всех"
                    if replace_all is True:
                        print(f"Заменяем пост с ID {post.id}.")
                    elif replace_all is False:
                        print(f"Пропускаем пост с ID {post.id}.")
                        continue  # Пропускаем обработку текущего поста
                    else:
                        # Диалог с пользователем
                        user_input = input("Пост уже существует. Хотите его заменить? (y/n/a): ").strip().lower()
                        if user_input == "y":
                            print(f"Заменяем пост с ID {post.id}.")
                        elif user_input == "n":
                            print(f"Пропускаем пост с ID {post.id}.")
                            continue  # Пропускаем обработку текущего поста
                        elif user_input == "a":
                            print("Выбрано 'да для всех'. Все существующие посты будут заменены.")
                            replace_all = True
                        else:
                            print("Неверный ввод. Пропускаем пост.")
                            continue
                else:
                    print(f"Неожиданный формат ответа от API: {response_data}")
            else:
                print(f"Ошибка при проверке существования поста: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Ошибка при проверке существования поста: {e}")
            continue
        
        # Проверяем, имеет ли пост комментарии
        if post.replies and post.replies.replies > 0:  # Если есть комментарии
            print(f"Пост с ID {post.id} имеет {post.replies.replies} комментариев.")

        # Преобразуем текст и entities в HTML
        formatted_message = parse_entities_to_html(post.message or "", post.entities or "")

        # Обрабатываем опрос, если он есть
        if post.poll:
            poll_html = process_poll(post)
            formatted_message += f"<br>{poll_html}"

        # Получаем папку для текущего канала
        channel_folder = get_channel_folder(channel_username)

        # Скачиваем медиа
        media_path = None
        media_type = None
        mime_type = None

        if post.media and not post.poll:  # Пропускаем скачивание медиа для опросов
            media_type = type(post.media).__name__  # Тип медиа (например, MessageMediaPhoto)
            
            # Обрабатываем MessageMediaWebPage
            if isinstance(post.media, MessageMediaWebPage):
                # Для веб-страниц сохраняем URL страницы в media_url
                if hasattr(post.media, 'webpage') and post.media.webpage and hasattr(post.media.webpage, 'url'):
                    media_path = post.media.webpage.url
                    logging.info(f"MessageMediaWebPage detected in main(): saving URL {media_path}")
            else:
                # Для остальных типов медиа скачиваем файлы
                media_path = client.download_media(
                    post.media,
                    file=os.path.join(channel_folder, "media", f"{post.id}_media")
                )
                # Сохраняем относительный путь для файлов
                if media_path:
                    media_path = os.path.relpath(media_path, DOWNLOADS_DIR)  # Относительный путь от папки downloads
            
            if isinstance(post.media, MessageMediaDocument) and isinstance(post.media.document, Document):
                mime_type = getattr(post.media.document, 'mime_type', None)

        # Обрабатываем автора сообщения
        sender_name, sender_avatar, sender_link = process_author(post.sender, client, channel_folder, peer_id=post.peer_id, from_id=post.from_id)

        # Обрабатываем автора репоста, если это репост
        repost_name, repost_avatar, repost_link = None, None, None
        if post.fwd_from and post.fwd_from.from_id:
            try:
                repost_entity = client.get_entity(post.fwd_from.from_id)  # Получаем полную информацию об авторе репоста
                repost_name, repost_avatar, repost_link = process_author(repost_entity, client, channel_folder)
            except Exception as e:
                print(f"Ошибка при обработке автора репоста: {e}")

        # Обрабатываем реакции
        reactions = None
        if post.reactions and post.reactions.results:
            reactions = {
                "total_count": sum(r.count for r in post.reactions.results),  # Суммируем количество всех реакций
                "recent_reactions": [
                    {"reaction": str(r.reaction), "count": r.count} for r in post.reactions.results
                ]
            }

        # Сохраняем данные в базу
        api_data = {
            "telegram_id": post.id,
            "channel_id": channel_username,  # Добавляем ID или имя канала
            "date": post.date.strftime('%Y-%m-%dT%H:%M:%S'),
            "message": formatted_message,
            "media_url": media_path,
            "media_type": media_type,
            "mime_type": mime_type,
            "author_name": sender_name,
            "author_avatar": sender_avatar,
            "author_link": sender_link,
            "repost_author_name": repost_name,
            "repost_author_avatar": repost_avatar,
            "repost_author_link": repost_link,
            "reactions": reactions  # Добавляем реакции
        }
        print("Отправляемые данные:", api_data)
        try:
            response = requests.post("http://127.0.0.1:5000/api/posts", json=api_data)
            if response.status_code == 201:
                print(f"Пост {post.id} успешно добавлен в базу данных.")
            else:
                print(f"Ошибка при добавлении поста {post.id}: {response.text}")
        except Exception as e:
            print(f"Ошибка при подключении к API: {e}")

        processed_count += 1

    client.disconnect()

    elapsed_time = time.time() - start_time
    print(f"Экспорт завершён за {elapsed_time:.2f} секунд.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Экспорт постов Telegram в базу данных.")
    parser.add_argument(
        "--channel",
        required=True,
        help="Имя Telegram-канала (без @), из которого нужно экспортировать посты."
    )
    args = parser.parse_args()

    # Передаём имя канала из аргументов
    channel_username = args.channel

    main(channel_username=channel_username)