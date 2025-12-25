"""
API endpoints для работы с каналами
"""
import os
import re
import time
import shutil
import requests
from flask import Blueprint, jsonify, request, current_app
from models import db, Post, Channel
from telegram_client import connect_to_telegram
from message_processing.channel_info import get_channel_info

channels_bp = Blueprint('channels', __name__)

# Константы
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'downloads')

@channels_bp.route('/channels', methods=['GET'])
def get_channels():
    """Возвращает список всех каналов."""
    channels = Channel.query.all()
    return jsonify([{
        "id": channel.id,
        "name": channel.name,
        "avatar": channel.avatar,
        "description": channel.description,
        "creation_date": channel.creation_date,
        "subscribers": channel.subscribers,
        "posts_count": channel.posts_count,
        "comments_count": channel.comments_count,
        "discussion_group_id": channel.discussion_group_id,
        "changes": channel.changes if hasattr(channel, 'changes') else {}
    } for channel in channels])

@channels_bp.route('/channels', methods=['POST'])
def add_channel_to_db():
    """Добавляет новый канал в базу данных."""
    data = request.json
    if not data.get('id') or not data.get('name'):
        return jsonify({"error": "id и name обязательны"}), 400

    # Проверяем, существует ли канал
    existing_channel = Channel.query.filter_by(id=data['id']).first()
    if existing_channel:
        return jsonify({"message": "Канал уже существует"}), 200

    # Добавляем новый канал
    new_channel = Channel(
        id=data['id'],
        name=data['name'],
        avatar=data.get('avatar'),
        creation_date=data.get('creation_date'),  # <-- должно быть!
        subscribers=data.get('subscribers'),
        description=data.get('description'),
        posts_count=data.get('posts_count'),
        comments_count=data.get('comments_count'),
        discussion_group_id=data.get('discussion_group_id'),
        changes=data.get('changes', {})
    )
    db.session.add(new_channel)
    db.session.commit()
    return jsonify({"message": "Канал успешно добавлен"}), 201

@channels_bp.route('/add_channel', methods=['POST'])
def run_channel_import():
    """Импортирует канал или переписку с пользователем напрямую через API."""
    current_app.logger.info('Добавление канала запущено')
    data = request.json
    current_app.logger.info(f"Получены данные: {data}")
    channel_username = data.get('channel_username')
    export_settings = data.get('export_settings', {})

    if not channel_username:
        current_app.logger.error("channel_username обязателен")
        return jsonify({"error": "channel_username обязателен"}), 400

    try:
        # Импорт функций для работы с каналами
        from utils.entity_validation import get_entity_by_username_or_id
        from telegram_export import import_channel_direct
        
        # Подключаемся к Telegram для получения реального ID
        client = connect_to_telegram()
        entity, error_message = get_entity_by_username_or_id(client, channel_username)
        
        if entity is None:
            return jsonify({"error": error_message}), 400
        
        # Определяем реальный ID для проверки в базе
        real_id = entity.username or str(entity.id)
        
        # Импорт функций для статуса загрузки
        import app
        
        # Устанавливаем статус начала загрузки
        app.set_download_status(real_id, 'downloading', {
            'channel_name': channel_username,
            'started_at': time.time(),
            'processed_posts': 0,
            'processed_comments': 0
        })
        
        # Проверяем, существует ли канал по реальному ID
        existing_channel = Channel.query.filter_by(id=real_id).first()
        if existing_channel:
            current_app.logger.warning(f"Канал/пользователь {real_id} уже существует.")
            return jsonify({"error": f"Канал/пользователь {real_id} уже импортирован"}), 400

        # Импортируем канал напрямую через API
        result = import_channel_direct(channel_username, real_id, export_settings)
        
        if result['success']:
            processed_count = result.get('processed', 0)
            comments_count = result.get('comments', 0)
            message = f"Канал/пользователь {real_id} успешно добавлен. Импортировано {processed_count} сообщений"
            if comments_count > 0:
                message += f" и {comments_count} комментариев"
            
            # Устанавливаем статус завершения
            app.set_download_status(real_id, 'completed', {
                'channel_name': channel_username,
                'completed_at': time.time(),
                'processed_posts': processed_count,
                'processed_comments': comments_count,
                'message': message
            })
            
            current_app.logger.info(message)
            return jsonify({"message": message}), 200
        else:
            # Устанавливаем статус ошибки
            app.set_download_status(real_id, 'error', {
                'channel_name': channel_username,
                'error_at': time.time(),
                'error': result['error']
            })
            
            current_app.logger.error(f"Ошибка импорта канала: {result['error']}")
            return jsonify({"error": result['error']}), 500
            
    except Exception as e:
        # Устанавливаем статус ошибки, если real_id определен
        if 'real_id' in locals():
            app.set_download_status(real_id, 'error', {
                'channel_name': channel_username,
                'error_at': time.time(),
                'error': str(e)
            })
        
        current_app.logger.error(f"Исключение: {str(e)}")
        return jsonify({"error": str(e)}), 500

@channels_bp.route('/channels/<channel_id>', methods=['GET'])
def get_channel(channel_id):
    """Возвращает информацию о конкретном канале."""
    channel = Channel.query.filter_by(id=channel_id).first()
    if not channel:
        return jsonify({"error": "Канал не найден"}), 404
    
    return jsonify({
        "id": channel.id,
        "name": channel.name,
        "avatar": channel.avatar,
        "description": channel.description,
        "creation_date": channel.creation_date,
        "subscribers": channel.subscribers,
        "discussion_group_id": channel.discussion_group_id,
        "changes": channel.changes if hasattr(channel, 'changes') else {}
    })

@channels_bp.route('/channels/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """Удаляет канал и связанные с ним данные."""
    try:
        # Получаем информацию о канале
        channel = Channel.query.filter_by(id=channel_id).first()
        if not channel:
            current_app.logger.warning(f"Канал с ID {channel_id} не найден.")
            return jsonify({"error": "Канал не найден"}), 404

        discussion_group_id = channel.discussion_group_id
        
        # Удаляем канал из таблицы channels
        db.session.delete(channel)
        current_app.logger.info(f"Канал с ID {channel_id} удалён из таблицы channels.")

        # Удаляем все посты, связанные с этим каналом
        posts_deleted = Post.query.filter_by(channel_id=channel_id).delete()
        current_app.logger.info(f"Удалено {posts_deleted} постов, связанных с каналом {channel_id}.")

        # Если у канала есть дискуссионная группа, удаляем и её
        if discussion_group_id:
            # Удаляем дискуссионную группу из таблицы channels
            discussion_group = Channel.query.filter_by(id=str(discussion_group_id)).first()
            if discussion_group:
                db.session.delete(discussion_group)
                current_app.logger.info(f"Дискуссионная группа с ID {discussion_group_id} удалена из таблицы channels.")
            
            # Удаляем все посты из дискуссионной группы
            discussion_posts_deleted = Post.query.filter_by(channel_id=str(discussion_group_id)).delete()
            current_app.logger.info(f"Удалено {discussion_posts_deleted} постов из дискуссионной группы {discussion_group_id}.")
            
            # Удаляем папку дискуссионной группы
            discussion_folder_name = f"channel_{discussion_group_id}" if str(discussion_group_id).isdigit() else str(discussion_group_id)
            discussion_folder = os.path.join(DOWNLOADS_DIR, discussion_folder_name)
            if os.path.exists(discussion_folder):
                shutil.rmtree(discussion_folder)
                current_app.logger.info(f"Папка дискуссионной группы {discussion_folder} удалена.")

        # Удаляем папку из /downloads
        channel_folder_name = f"channel_{channel_id}" if channel_id.isdigit() else channel_id
        channel_folder = os.path.join(DOWNLOADS_DIR, channel_folder_name)
        if os.path.exists(channel_folder):
            shutil.rmtree(channel_folder)
            current_app.logger.info(f"Папка {channel_folder} удалена.")

        # Применяем изменения
        db.session.commit()

        return jsonify({"message": f"Канал {channel_id} и все связанные данные успешно удалены."}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при удалении канала {channel_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@channels_bp.route('/channels/<channel_id>', methods=['PUT'])
def update_channel(channel_id):
    """Обновляет информацию о канале, включая поле changes."""
    try:
        channel = Channel.query.filter_by(id=channel_id).first()
        if not channel:
            return jsonify({"error": "Канал не найден"}), 404
        
        data = request.json
        if not data:
            return jsonify({"error": "Нет данных для обновления"}), 400
        
        # Обновляем поля канала
        if 'name' in data:
            channel.name = data['name']
        if 'avatar' in data:
            channel.avatar = data['avatar']
        if 'description' in data:
            channel.description = data['description']
        if 'creation_date' in data:
            channel.creation_date = data['creation_date']
        if 'subscribers' in data:
            channel.subscribers = data['subscribers']
        if 'discussion_group_id' in data:
            channel.discussion_group_id = data['discussion_group_id']
        if 'changes' in data:
            channel.changes = data['changes']
        
        db.session.commit()
        
        return jsonify({
            "message": "Канал успешно обновлен",
            "id": channel.id,
            "name": channel.name,
            "avatar": channel.avatar,
            "description": channel.description,
            "creation_date": channel.creation_date,
            "subscribers": channel.subscribers,
            "discussion_group_id": channel.discussion_group_id,
            "changes": channel.changes if hasattr(channel, 'changes') else {}
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Ошибка при обновлении канала {channel_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@channels_bp.route('/channel_preview', methods=['GET'])
def channel_preview():
    """Предварительный просмотр канала перед импортом."""
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Не передан username'}), 400
    
    current_app.logger.info(f"Запрос на preview канала: {username}")
    
    client = None
    try:
        current_app.logger.info("Подключение к Telegram...")
        
        # Обработка проблем с event loop
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        client = connect_to_telegram()
        current_app.logger.info("Успешно подключились к Telegram")
        
        current_app.logger.info(f"Получение entity для канала/пользователя: {username}")
        
        # Получаем entity по username или ID
        from utils.entity_validation import get_entity_by_username_or_id, validate_entity_for_download
        entity, error_message = get_entity_by_username_or_id(client, username)
        
        if entity is None:
            return jsonify({'error': error_message}), 400
            
        current_app.logger.info(f"Успешно получен entity: {type(entity).__name__}")
        
        # Проверяем, что это публичный канал или пользователь
        validation_result = validate_entity_for_download(entity, username)
        
        if not validation_result["valid"]:
            return jsonify({'error': validation_result["error"]}), 400
        
        entity_type = validation_result["type"]
        
        # Определяем имя папки
        folder_name = entity.username or f"user_{entity.id}" if hasattr(entity, 'first_name') else entity.username or f"channel_{entity.id}"
        
        current_app.logger.info(f"Получение информации о {entity_type}: {username}")
        info = get_channel_info(client, entity, output_dir="downloads", folder_name=folder_name)
        current_app.logger.info(f"Информация о {entity_type} успешно получена")
        
        return jsonify(info)
    except Exception as e:
        current_app.logger.error(f"Ошибка в channel_preview для {username}: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    finally:
        # НЕ закрываем клиент, так как он глобальный и переиспользуется
        # Только логируем завершение запроса
        if client:
            current_app.logger.info("Запрос к Telegram завершен")

def clean_css_for_pdf(css_content):
    """
    Очищает CSS от проблемных правил для WeasyPrint
    """
    # Удаляем пустые CSS custom properties, которые вызывают warnings
    # Например: --tw-gradient-via-position: ;
    css_content = re.sub(r'--tw-[^:]*:\s*;', '', css_content)
    css_content = re.sub(r'--[^:]*:\s*;', '', css_content)
    
    return css_content

def process_html_for_standalone(html_content):
    """
    Обрабатывает HTML для автономного использования:
    - Встраивает CSS стили inline
    - Удаляет ссылки на внешние стили
    - Добавляет meta-теги для корректного отображения
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Удаляем все ссылки на CSS файлы
    for link in soup.find_all('link', rel='stylesheet'):
        link.decompose()
    
    # Добавляем ссылку на локальный CSS файл
    head = soup.find('head')
    if head:
        css_link = soup.new_tag('link')
        css_link['rel'] = 'stylesheet'
        css_link['href'] = './styles.css'
        head.append(css_link)
    
    # Удаляем скрипты (для статичного HTML они не нужны)
    for script in soup.find_all('script'):
        script.decompose()
    
    # Добавляем базовые meta-теги если их нет
    head = soup.find('head')
    if head:
        if not soup.find('meta', charset=True):
            meta_charset = soup.new_tag('meta')
            meta_charset['charset'] = 'utf-8'
            head.insert(0, meta_charset)
        
        if not soup.find('meta', attrs={'name': 'viewport'}):
            meta_viewport = soup.new_tag('meta')
            meta_viewport['name'] = 'viewport'
            meta_viewport['content'] = 'width=device-width, initial-scale=1.0'
            head.append(meta_viewport)
    
    # Обновляем пути к медиа файлам на относительные
    # (они уже должны быть в папке downloads/channel_id/media/)
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and src.startswith('/api/media/'):
            # Заменяем /api/media/channel_id/filename на ./media/filename
            filename = src.split('/')[-1]
            img['src'] = f'./media/{filename}'
    
    return str(soup)

@channels_bp.route('/channels/<channel_id>/export-html', methods=['GET'])
def export_channel_to_html(channel_id):
    """Экспортирует канал в HTML формат для автономного использования."""
    try:
        # Получаем HTML от SSR с параметром export=1 для включения режима экспорта
        ssr_url = f'http://ssr:3000/{channel_id}/posts?export=1'
        current_app.logger.info(f"🔍 [BACKEND] Making SSR request to: {ssr_url}")
        
        response = requests.get(ssr_url)
        current_app.logger.info(f"🔍 [BACKEND] SSR response status: {response.status_code}")
        
        if response.status_code != 200:
            current_app.logger.error(f"SSR-сервер вернул ошибку: {response.status_code}")
            return jsonify({"error": "Ошибка SSR-рендеринга"}), 500

        html_content = response.text
        
        # Создаем папку для канала в downloads
        channel_dir = os.path.join(DOWNLOADS_DIR, channel_id)
        os.makedirs(channel_dir, exist_ok=True)
        
        # Копируем CSS файл из tg-offliner-frontend/public/styles.css
        css_source = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tg-offliner-frontend', 'public', 'styles.css')
        css_dest = os.path.join(channel_dir, 'styles.css')
        
        try:
            if os.path.exists(css_source):
                shutil.copy2(css_source, css_dest)
                current_app.logger.info(f"CSS файл скопирован: {css_source} -> {css_dest}")
            else:
                current_app.logger.warning(f"CSS файл не найден: {css_source}")
        except Exception as css_error:
            current_app.logger.error(f"Ошибка при копировании CSS: {css_error}")
        
        # Обрабатываем HTML для автономного использования
        processed_html = process_html_for_standalone(html_content)
        
        # Сохраняем HTML файл
        html_path = os.path.join(channel_dir, 'index.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(processed_html)

        if not os.path.exists(html_path):
            current_app.logger.error(f"HTML-файл не найден после создания: {html_path}")
            return jsonify({"error": "HTML-файл не был создан"}), 500

        current_app.logger.info(f"HTML для канала {channel_id} успешно создан: {html_path}")
        return jsonify({"success": True, "message": f"HTML файл создан в {html_path}"}), 200
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при экспорте HTML для канала {channel_id}: {str(e)}")
        return jsonify({"error": "Ошибка при экспорте HTML"}), 500

def create_pdf_html(channel_id):
    """Создает HTML специально для PDF с минимальным CSS."""
    try:
        # Получаем HTML от SSR
        ssr_url = f'http://ssr:3000/{channel_id}/posts'
        response = requests.get(ssr_url)
        if response.status_code != 200:
            current_app.logger.error(f"SSR-сервер вернул ошибку: {response.status_code}")
            return None

        html_content = response.text
        
        # Создаем папку для канала
        channel_dir = os.path.join(DOWNLOADS_DIR, channel_id)
        os.makedirs(channel_dir, exist_ok=True)
        
        # Копируем PDF CSS файл 
        pdf_css_source = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tg-offliner-frontend', 'public', 'styles-pdf.css')
        pdf_css_dest = os.path.join(channel_dir, 'styles-pdf.css')
        
        if os.path.exists(pdf_css_source):
            # Читаем CSS файл
            with open(pdf_css_source, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Очищаем CSS от проблемных конструкций
            cleaned_css = clean_css_for_pdf(css_content)
            
            # Сохраняем очищенный CSS
            with open(pdf_css_dest, 'w', encoding='utf-8') as f:
                f.write(cleaned_css)
            
            current_app.logger.info(f"PDF CSS файл скопирован и очищен: {pdf_css_source} -> {pdf_css_dest}")
        else:
            current_app.logger.warning(f"PDF CSS файл не найден: {pdf_css_source}")
            return None
        
        # Обрабатываем HTML для PDF
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Удаляем все существующие CSS ссылки
        for link in soup.find_all('link', rel='stylesheet'):
            link.decompose()
        
        # Добавляем ссылку на PDF CSS
        head = soup.find('head')
        if head:
            css_link = soup.new_tag('link')
            css_link['rel'] = 'stylesheet'
            css_link['href'] = './styles-pdf.css'
            head.append(css_link)
        
        # Удаляем скрипты
        for script in soup.find_all('script'):
            script.decompose()
        
        # Добавляем базовые meta-теги
        if head:
            if not soup.find('meta', charset=True):
                meta_charset = soup.new_tag('meta')
                meta_charset['charset'] = 'utf-8'
                head.insert(0, meta_charset)
        
        # Обновляем пути к медиа файлам
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src.startswith('/api/media/'):
                filename = src.split('/')[-1]
                img['src'] = f'./media/{filename}'
        
        # Сохраняем PDF HTML
        pdf_html_path = os.path.join(channel_dir, 'index-pdf.html')
        with open(pdf_html_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        current_app.logger.info(f"PDF HTML создан: {pdf_html_path}")
        return pdf_html_path
        
    except Exception as e:
        current_app.logger.error(f"Ошибка при создании PDF HTML: {str(e)}")
        return None

@channels_bp.route('/channels/<channel_id>/print', methods=['GET'])
def print_channel_to_pdf(channel_id):
    """Экспортирует канал в PDF формат с минимальным CSS."""
    # Повышаем лимит рекурсии в самом начале
    import sys
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(50000)
    
    try:
        current_app.logger.info(f"=== НАЧАЛО PDF ГЕНЕРАЦИИ для канала {channel_id} ===")
        current_app.logger.info(f"Лимит рекурсии изменен с {old_limit} на 50000")
        
        # Создаем специальный HTML для PDF
        current_app.logger.info("Создание PDF HTML с минимальным CSS...")
        pdf_html_path = create_pdf_html(channel_id)
        
        if not pdf_html_path or not os.path.exists(pdf_html_path):
            current_app.logger.error("PDF HTML не был создан")
            return jsonify({"error": "Ошибка при создании PDF HTML"}), 500
        
        current_app.logger.info(f"PDF HTML создан: {pdf_html_path}")
        
        # Генерируем PDF из локального HTML файла
        current_app.logger.info("Импорт weasyprint...")
        from weasyprint import HTML
        
        channel_dir = os.path.join(DOWNLOADS_DIR, channel_id)
        pdf_path = os.path.join(channel_dir, f"{channel_id}.pdf")
        current_app.logger.info(f"Начинаем генерацию PDF: {pdf_path}")
        
        HTML(filename=pdf_html_path).write_pdf(pdf_path)
        current_app.logger.info("PDF успешно сгенерирован")

        if not os.path.exists(pdf_path):
            current_app.logger.error(f"PDF-файл не найден после генерации: {pdf_path}")
            return jsonify({"error": "PDF-файл не был создан"}), 500

        current_app.logger.info(f"PDF для канала {channel_id} успешно создан: {pdf_path}")
        
        return jsonify({
            "success": True, 
            "message": f"PDF файл создан и сохранен в папку downloads/{channel_id}/",
            "path": pdf_path
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f"ОШИБКА при генерации PDF для канала {channel_id}")
        return jsonify({"error": f"Ошибка при генерации PDF: {str(e)}"}), 500
        
    finally:
        # Восстанавливаем лимит рекурсии в любом случае
        sys.setrecursionlimit(old_limit)
        current_app.logger.info(f"Лимит рекурсии восстановлен до {old_limit}")
        current_app.logger.info("=== КОНЕЦ PDF ГЕНЕРАЦИИ ===")

@channels_bp.route('/channels/<channel_id>/export-idml', methods=['GET'])
def export_channel_to_idml(channel_id):
    """Экспортирует канал в IDML формат для InDesign."""
    try:
        current_app.logger.info(f"=== НАЧАЛО IDML ЭКСПОРТА для канала {channel_id} ===")
        
        # Получаем канал и его посты
        channel = Channel.query.filter_by(id=channel_id).first()
        if not channel:
            return jsonify({"error": "Канал не найден"}), 404
        
        # Получаем настройки печати канала
        print_settings = channel.print_settings or {}
        
        # Получаем все видимые посты (не hidden)
        # TODO: позже добавим фильтрацию по hidden через Edits
        posts = Post.query.filter_by(channel_id=channel_id).order_by(Post.telegram_id.asc()).limit(10).all()
        
        if not posts:
            return jsonify({"error": "В канале нет постов для экспорта"}), 404
        
        current_app.logger.info(f"Найдено {len(posts)} постов для экспорта")
        
        # Создаем IDML builder
        from idml_export.builder import IDMLBuilder
        
        builder = IDMLBuilder(channel, print_settings)
        builder.create_document()
        
        # Добавляем тестовый пост (пока просто текст)
        for post in posts:
            # Получаем индивидуальные настройки поста
            post_settings = post.print_settings or {}
            
            # Текст поста
            if post.message:
                story_id = builder.add_text_story(post.message, 'PostBody')
                
                # Вычисляем bounds для текстового фрейма
                # Упрощенная версия - просто добавляем под текущей позицией
                from idml_export.coordinates import calculate_text_frame_bounds
                page_bounds = builder.current_page['bounds']
                text_area = calculate_text_frame_bounds(
                    page_bounds,
                    builder.settings['margins']
                )
                
                # Простой фрейм высотой 150pt
                frame_bounds = [
                    builder.current_y,
                    text_area['bounds'][1],
                    builder.current_y + 150,
                    text_area['bounds'][3]
                ]
                
                builder.add_text_frame(story_id, frame_bounds)
                builder.current_y += 160  # +10 для отступа между постами
        
        # Сохраняем IDML
        channel_dir = os.path.join(DOWNLOADS_DIR, channel_id)
        os.makedirs(channel_dir, exist_ok=True)
        
        idml_path = os.path.join(channel_dir, f"{channel_id}.idml")
        builder.save(idml_path)
        
        if not os.path.exists(idml_path):
            current_app.logger.error(f"IDML файл не найден после создания: {idml_path}")
            return jsonify({"error": "IDML файл не был создан"}), 500
        
        current_app.logger.info(f"IDML для канала {channel_id} успешно создан: {idml_path}")
        current_app.logger.info("=== КОНЕЦ IDML ЭКСПОРТА ===")
        
        return jsonify({
            "success": True,
            "message": f"IDML файл создан в downloads/{channel_id}/{channel_id}.idml",
            "path": idml_path
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f"ОШИБКА при экспорте IDML для канала {channel_id}")
        return jsonify({"error": f"Ошибка при экспорте IDML: {str(e)}"}), 500
