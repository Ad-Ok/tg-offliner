from telethon.sync import TelegramClient
from config import EXPORT_SETTINGS
from telegram_client import connect_to_telegram
import time
import argparse
import requests
import os
import shutil
import logging
from message_processing.channel_info import get_channel_info
from message_processing.message_transform import (
    DOWNLOADS_DIR as TRANSFORM_DOWNLOADS_DIR,
    process_message_for_api,
    get_channel_folder,
)
from utils.gallery_layout import generate_gallery_layout
from utils.entity_validation import get_entity_by_username_or_id
from utils.import_state import should_stop as _state_should_stop, update_progress as _state_update_progress

# Настройка логирования
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

DOWNLOADS_DIR = TRANSFORM_DOWNLOADS_DIR

def should_stop_import(channel_id):
    """Проверяет, нужно ли остановить импорт (через shared state, без HTTP)"""
    if not channel_id:
        return False
    return _state_should_stop(channel_id)

def update_import_progress(channel_id, processed_posts, processed_comments, total_posts=None):
    """Обновляет прогресс импорта (через shared state, без HTTP)"""
    if not channel_id:
        return
    _state_update_progress(channel_id, processed_posts, total_posts or 0, processed_comments)

BATCH_SIZE = 50


def _flush_batch(batch):
    """Записывает пачку постов в БД за один commit (без HTTP)."""
    if not batch:
        return
    from app import app
    from models import db, Post

    with app.app_context():
        for data in batch:
            new_post = Post(
                telegram_id=data['telegram_id'],
                channel_id=data['channel_id'],
                date=data['date'],
                message=data.get('message', ''),
                media_url=data.get('media_url'),
                thumb_url=data.get('thumb_url'),
                media_type=data.get('media_type'),
                mime_type=data.get('mime_type'),
                author_name=data.get('author_name'),
                author_avatar=data.get('author_avatar'),
                author_link=data.get('author_link'),
                repost_author_name=data.get('repost_author_name'),
                repost_author_avatar=data.get('repost_author_avatar'),
                repost_author_link=data.get('repost_author_link'),
                reactions=data.get('reactions'),
                grouped_id=data.get('grouped_id'),
                reply_to=data.get('reply_to'),
            )
            db.session.add(new_post)
        db.session.commit()
    logging.info(f"Batch: записано {len(batch)} постов в БД")


def _save_channel(channel_info):
    """Сохраняет канал в БД напрямую (без HTTP). Возвращает True при успехе."""
    try:
        from app import app
        from models import db, Channel

        with app.app_context():
            existing = Channel.query.filter_by(id=channel_info['id']).first()
            if existing:
                logging.info(f"Канал {channel_info['id']} уже существует в БД")
                return True
            new_channel = Channel(
                id=channel_info['id'],
                name=channel_info['name'],
                avatar=channel_info.get('avatar'),
                creation_date=channel_info.get('creation_date'),
                subscribers=channel_info.get('subscribers'),
                description=channel_info.get('description'),
                posts_count=channel_info.get('posts_count'),
                comments_count=channel_info.get('comments_count'),
                discussion_group_id=channel_info.get('discussion_group_id'),
                changes=channel_info.get('changes', {})
            )
            db.session.add(new_channel)
            db.session.commit()
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения канала {channel_info.get('id')}: {e}")
        return False


def import_channel_direct(channel_username, channel_id=None, export_settings=None):
    """
    Импортирует канал или переписку с пользователем напрямую, используя существующий клиент.
    Возвращает словарь с результатом.
    
    :param channel_username: Имя канала или пользователя
    :param channel_id: ID канала для отслеживания статуса (опционально)
    :param export_settings: Настройки экспорта (опционально)
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
        
        # Добавляем канал в базу данных напрямую
        if not _save_channel(channel_info):
            return {"success": False, "error": "Ошибка добавления канала в БД"}
        
        # Импортируем сообщения
        # Используем переданные настройки или значения по умолчанию
        if export_settings:
            include_system_messages = export_settings.get("include_system_messages", False)
            include_reposts = export_settings.get("include_reposts", True)
            include_polls = export_settings.get("include_polls", True)
            include_discussion_comments = export_settings.get("include_discussion_comments", True)
            message_limit = export_settings.get("message_limit", None)
        else:
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
        
        logging.info(f"Всего постов в канале {channel_username}: {total_posts}")
        logging.info(f"Начинаем обработку постов из канала {channel_username}")
        
        post_iteration = 0
        batch = []
        for post in all_posts:
            post_iteration += 1
            logging.info(f"Итерация {post_iteration}: обрабатываем пост {post.id}")
            try:
                # Проверяем, нужно ли остановить импорт
                if should_stop_import(channel_id):
                    _flush_batch(batch)
                    batch = []
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
                
                # Обрабатываем сообщение
                logging.info(f"Обрабатываем пост {post.id} из канала {channel_username}")
                try:
                    post_data = process_message_for_api(post, real_id, client, folder_name)
                except Exception as e:
                    logging.error(f"Ошибка в process_message_for_api для поста {post.id}: {str(e)}")
                    post_data = None
                if post_data:
                    batch.append(post_data)
                    processed_count += 1
                    logging.info(f"Пост {post.id} добавлен в batch, всего: {processed_count}")
                    
                    if len(batch) >= BATCH_SIZE:
                        _flush_batch(batch)
                        batch = []
                else:
                    logging.warning(f"process_message_for_api вернул None для поста {post.id}")
                
                # Обновляем прогресс каждые 5 постов или на каждом посте, если постов мало
                if processed_count % 5 == 0 or total_posts < 50:
                    update_import_progress(channel_id, processed_count, comments_count, total_posts)
            except Exception as e:
                logging.error(f"Ошибка при обработке сообщения: {str(e)}")
        
        # Flush оставшихся постов в batch
        _flush_batch(batch)
        
        logging.info(f"Обработано сообщений: {processed_count}")
        logging.info(f"Канал {channel_username} импортирован: {processed_count} сообщений")
        
        # Импортируем ВСЕ комментарии из группы обсуждений за один проход
        if discussion_group_id and include_discussion_comments:
            logging.info(f"Начинаем импорт комментариев из группы обсуждений {discussion_group_id}...")
            comments_count = import_all_discussion_comments(
                client,
                real_id,
                discussion_group_id
            )
            logging.info(f"Импортировано комментариев: {comments_count}")
        
        # Финальное обновление прогресса
        update_import_progress(channel_id, processed_count, comments_count, total_posts)
        
        # Генерируем layouts для галерей
        generate_gallery_layouts_for_channel(channel_username)
        
        # Если есть дискуссионная группа, генерируем layouts и для неё
        if discussion_group_id:
            generate_gallery_layouts_for_channel(str(discussion_group_id))
        
        return {"success": True, "processed": processed_count, "comments": comments_count}
        
    except Exception as e:
        logging.error(f"Ошибка импорта канала {channel_username}: {str(e)}")
        return {"success": False, "error": str(e)}

def import_all_discussion_comments(client, channel_id, discussion_group_id):
    """
    Импортирует ВСЕ комментарии из группы обсуждений за один проход (streaming).
    Использует reverse_mapping для O(1) lookup и batch insert.
    
    :param client: Подключённый клиент Telethon
    :param channel_id: ID канала
    :param discussion_group_id: ID группы обсуждений
    :return: Количество импортированных комментариев
    """
    try:
        logging.info(f"Получаем все сообщения из группы обсуждений {discussion_group_id}")
        
        # Получаем entity группы обсуждений
        discussion_entity, error = get_entity_by_username_or_id(client, str(discussion_group_id))
        if discussion_entity is None:
            logging.error(f"Не удалось получить группу обсуждений {discussion_group_id}: {error}")
            return 0
        
        # Сохраняем информацию о дискуссионной группе
        try:
            save_discussion_group_info(client, discussion_entity)
        except Exception as e:
            logging.error(f"Ошибка сохранения дискуссионной группы: {e}")
        
        folder_name = f"channel_{discussion_group_id}"
        
        # Streaming: один проход с reverse=True (старые сообщения первыми)
        # Forwards (копии постов канала) идут хронологически раньше комментариев → меньше pending
        logging.info("Streaming импорт комментариев (один проход, reverse=True)...")
        
        reverse_mapping = {}   # forwarded_msg_id → original_post_id (O(1) lookup)
        pending = []           # Комментарии, для которых forward ещё не встретился
        batch = []
        comments_imported = 0
        message_count = 0
        forwards_count = 0
        
        for message in client.iter_messages(discussion_entity, reverse=True):
            message_count += 1
            
            # Если это форвард из канала — запоминаем маппинг
            if hasattr(message, 'fwd_from') and message.fwd_from:
                if hasattr(message.fwd_from, 'saved_from_msg_id') and message.fwd_from.saved_from_msg_id:
                    saved_id = message.fwd_from.saved_from_msg_id
                    reverse_mapping[message.id] = saved_id
                    forwards_count += 1
                    logging.debug(f"Форвард: пост {saved_id} -> msg {message.id}")
                continue  # Форварды пропускаем (не комментарии)
            
            # Пропускаем не-ответы
            if not (hasattr(message, 'reply_to') and message.reply_to and
                    hasattr(message.reply_to, 'reply_to_msg_id')):
                continue
            
            # Ищем оригинальный пост канала через reverse_mapping (O(1))
            original_post_id = None
            
            # reply_to_top_id — корень треда (обычно это forwarded message)
            top_id = getattr(message.reply_to, 'reply_to_top_id', None)
            if top_id:
                original_post_id = reverse_mapping.get(top_id)
            
            # Fallback: прямой ответ
            if original_post_id is None:
                reply_to_msg_id = message.reply_to.reply_to_msg_id
                original_post_id = reverse_mapping.get(reply_to_msg_id)
            
            if original_post_id is None:
                pending.append(message)
                continue
            
            # Обрабатываем комментарий
            try:
                comment_data = process_message_for_api(message, str(discussion_group_id), client, folder_name)
                if comment_data:
                    comment_data['reply_to'] = original_post_id
                    batch.append(comment_data)
                    comments_imported += 1
                    
                    if len(batch) >= BATCH_SIZE:
                        _flush_batch(batch)
                        batch = []
            except Exception as e:
                logging.error(f"Ошибка обработки комментария {message.id}: {e}")
            
            if message_count % 500 == 0:
                logging.info(f"  Обработано {message_count} сообщений, {forwards_count} форвардов, {comments_imported} комментариев, {len(pending)} pending")
        
        logging.info(f"Первый проход завершён: {message_count} сообщений, {forwards_count} форвардов, {comments_imported} комментариев, {len(pending)} pending")
        
        # Обрабатываем pending — теперь все forwards собраны
        if pending:
            logging.info(f"Обрабатываем {len(pending)} pending комментариев...")
            for message in pending:
                original_post_id = None
                
                top_id = getattr(message.reply_to, 'reply_to_top_id', None)
                if top_id:
                    original_post_id = reverse_mapping.get(top_id)
                
                if original_post_id is None:
                    reply_to_msg_id = message.reply_to.reply_to_msg_id
                    original_post_id = reverse_mapping.get(reply_to_msg_id)
                
                if original_post_id is None:
                    continue
                
                try:
                    comment_data = process_message_for_api(message, str(discussion_group_id), client, folder_name)
                    if comment_data:
                        comment_data['reply_to'] = original_post_id
                        batch.append(comment_data)
                        comments_imported += 1
                except Exception as e:
                    logging.error(f"Ошибка обработки pending комментария {message.id}: {e}")
        
        # Flush remaining batch
        _flush_batch(batch)
        
        logging.info(f"✅ Импортировано {comments_imported} комментариев")
        return comments_imported
        
    except Exception as e:
        logging.error(f"Ошибка импорта комментариев: {e}")
        return 0

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
        folder_name = f"channel_{discussion_group_id}"
        
        # Сначала ищем форвардированный пост в группе обсуждений
        forwarded_post_id = None
        comments_count = 0
        
        try:
            # Получаем настройки из конфигурации
            forward_search_limit = EXPORT_SETTINGS.get("comments_forward_search_limit", 500)
            comments_search_limit = EXPORT_SETTINGS.get("comments_search_limit", 1000)
            
            # Ищем среди последних сообщений форвардированный пост из канала
            recent_messages = client.iter_messages(discussion_entity, limit=forward_search_limit)
            
            forwards_found = 0
            for message in recent_messages:
                # Проверяем, является ли сообщение форвардом из нашего канала
                if (hasattr(message, 'fwd_from') and message.fwd_from):
                    forwards_found += 1
                    logging.info(f"=== Найден форвард message.id={message.id} ===")
                    logging.info(f"fwd_from: {message.fwd_from}")
                    logging.info(f"has from_id: {hasattr(message.fwd_from, 'from_id')}")
                    if hasattr(message.fwd_from, 'from_id'):
                        logging.info(f"from_id: {message.fwd_from.from_id}")
                    logging.info(f"has saved_from_msg_id: {hasattr(message.fwd_from, 'saved_from_msg_id')}")
                    if hasattr(message.fwd_from, 'saved_from_msg_id'):
                        logging.info(f"saved_from_msg_id: {message.fwd_from.saved_from_msg_id}, original_post_id: {original_post_id}")
                        if message.fwd_from.saved_from_msg_id == original_post_id:
                            forwarded_post_id = message.id
                            logging.info(f"✅ Найден форвардированный пост {forwarded_post_id} для оригинального поста {original_post_id}")
                            break
                    
                    # Альтернативный поиск: проверяем дату и содержимое
                    # Иногда saved_from_msg_id может отсутствовать
                    if hasattr(message.fwd_from, 'date'):
                        logging.debug(f"Проверяем форвард с датой {message.fwd_from.date}")
            
            logging.info(f"Всего найдено форвардов при поиске для поста {original_post_id}: {forwards_found}")
            
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
        discussion_info = get_channel_info(client, discussion_entity, output_dir="downloads", folder_name=f"channel_{discussion_entity.id}")
        discussion_info["id"] = str(discussion_entity.id)
        
        # Добавляем метку, что это дискуссионная группа
        discussion_info["name"] = f"💬 {discussion_info['name']} (обсуждения)"
        
        # Убираем discussion_group_id, так как дискуссионная группа не должна ссылаться на другую группу
        discussion_info["discussion_group_id"] = None
        
        # Сохраняем в базу данных напрямую
        if _save_channel(discussion_info):
            logging.info(f"Информация о дискуссионной группе {discussion_entity.id} сохранена")
        else:
            logging.warning(f"Не удалось сохранить информацию о дискуссионной группе {discussion_entity.id}")
    except Exception as e:
        logging.error(f"Ошибка сохранения информации о дискуссионной группе {discussion_entity.id}: {e}")
def clear_downloads(channel_name):
    """
    Очищает папку текущего канала в downloads, но не удаляет саму папку downloads.
    """
    channel_folder = os.path.join(DOWNLOADS_DIR, channel_name)
    if os.path.exists(channel_folder):
        shutil.rmtree(channel_folder)  # Удаляем папку канала со всем содержимым
        print(f"Папка {channel_folder} очищена.")
    os.makedirs(channel_folder, exist_ok=True)  # Создаём пустую папку

def generate_gallery_layouts_for_channel(channel_username):
    """Генерирует JSON layouts для галерей в канале и сохраняет в базу данных."""
    logging.info(f"Generating gallery layouts for channel: {channel_username}")
    try:
        # Работаем напрямую с базой
        from app import app
        with app.app_context():
            from models import Post, Layout, db, Layout
            
            # Получаем все посты канала
            posts = Post.query.filter_by(channel_id=channel_username).all()
            logging.info(f"Found {len(posts)} posts in channel {channel_username}")
            
            # Группируем посты по grouped_id
            galleries = {}
            for post in posts:
                grouped_id = post.grouped_id
                if grouped_id and post.media_type == 'MessageMediaPhoto':
                    if grouped_id not in galleries:
                        galleries[grouped_id] = []
                    galleries[grouped_id].append(post)

            logging.info(f"Found galleries: {list(galleries.keys())}")
            
            for grouped_id, gallery_posts in galleries.items():
                logging.info(f"Processing gallery {grouped_id} with {len(gallery_posts)} posts")
                if len(gallery_posts) < 2:
                    logging.info(f"Skipping gallery {grouped_id} - only {len(gallery_posts)} images")
                    continue  # Пропускаем галереи с одним изображением

                # Сохраняем пользовательские правки: если layout уже есть, не пересоздаём его
                existing_layout = Layout.query.filter_by(grouped_id=grouped_id, channel_id=channel_username).first()
                if existing_layout:
                    logging.info(
                        "Layout for gallery %s already exists for channel %s, skipping auto generation",
                        grouped_id,
                        channel_username,
                    )
                    continue

                # Сортируем посты по telegram_id для консистентного порядка
                gallery_posts.sort(key=lambda p: p.telegram_id)

                # Собираем пути к превью
                image_paths = []
                for post in gallery_posts:
                    # Используем thumb_url из базы данных, если он есть
                    thumb_url = post.thumb_url
                    if thumb_url:
                        thumb_path = os.path.join(DOWNLOADS_DIR, thumb_url.lstrip('/'))
                        if os.path.exists(thumb_path):
                            image_paths.append(thumb_path)
                    else:
                        # Fallback: старый способ для совместимости
                        media_url = post.media_url
                        if media_url:
                            media_relative = media_url.lstrip('/')
                            thumb_path = os.path.join(
                                DOWNLOADS_DIR,
                                media_relative.replace('/media/', '/thumbs/')
                            )
                            if os.path.exists(thumb_path):
                                image_paths.append(thumb_path)

                logging.info(f"Gallery {grouped_id}: collected {len(image_paths)} image paths from {len(gallery_posts)} posts")

                if len(image_paths) >= 2:
                    # Генерируем layout
                    from utils.gallery_layout import generate_gallery_layout
                    layout_data = generate_gallery_layout(image_paths)
                    
                    if layout_data:
                        logging.info(f"Generated layout for gallery {grouped_id}: {len(layout_data.get('cells', []))} cells")
                        # Сохраняем в базу данных
                        new_layout = Layout(grouped_id=grouped_id, channel_id=channel_username, json_data=layout_data)
                        db.session.add(new_layout)
                        db.session.commit()
                        print(f"Generated and saved layout for gallery {grouped_id}")

    except Exception as e:
        print(f"Error generating gallery layouts: {e}")

def main(channel_username=None):
    """
    Точка входа для импорта канала.
    Парсит аргументы и вызывает import_channel_direct().
    
    :param channel_username: Имя канала или пользователя
    """
    start_time = time.time()
    
    try:
        # Вызываем основную функцию импорта
        result = import_channel_direct(channel_username)
        
        elapsed_time = time.time() - start_time
        
        if result["success"]:
            print(f"✅ Импорт завершён за {elapsed_time:.2f} секунд.")
            print(f"   Постов обработано: {result['processed']}")
            print(f"   Комментариев импортировано: {result['comments']}")
            if result.get("stopped"):
                print(f"   ⚠️ Импорт был остановлен пользователем")
        else:
            print(f"❌ Ошибка при импорте: {result['error']}")
            
    except Exception as e:
        logging.error(f"Критическая ошибка в main(): {e}")
        print(f"❌ Критическая ошибка: {e}")

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