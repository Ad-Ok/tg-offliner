"""
API endpoints для управления загрузками
"""
import time
from flask import Blueprint, jsonify, request, current_app

downloads_bp = Blueprint('downloads', __name__)

# Импорт функций для работы со статусами загрузки
def get_download_globals():
    """Получает глобальные переменные для загрузки из основного приложения"""
    import app
    return app.download_status, app.download_lock, app.get_download_status, app.set_download_status, app.update_download_progress

@downloads_bp.route('/download/status', methods=['GET'])
def get_download_statuses():
    """Возвращает статусы всех загрузок."""
    download_status, download_lock, _, _, _ = get_download_globals()
    with download_lock:
        return jsonify(download_status), 200

@downloads_bp.route('/download/status/<channel_id>', methods=['GET'])
def get_download_status_api(channel_id):
    """Возвращает статус загрузки канала."""
    _, _, get_download_status, _, _ = get_download_globals()
    status = get_download_status(channel_id)
    if status:
        return jsonify(status), 200
    else:
        return jsonify({"status": "not_found", "details": {}}), 404

@downloads_bp.route('/download/progress/<channel_id>', methods=['POST'])
def update_progress(channel_id):
    """Обновляет прогресс загрузки канала"""
    try:
        _, _, _, _, update_download_progress = get_download_globals()
        
        data = request.get_json()
        posts_processed = data.get('posts_processed', 0)
        total_posts = data.get('total_posts', 0)
        comments_processed = data.get('comments_processed', 0)
        
        update_download_progress(channel_id, posts_processed, total_posts, comments_processed)
        return jsonify({'message': 'Прогресс обновлен'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@downloads_bp.route('/download/stop/<channel_id>', methods=['POST'])
def stop_download(channel_id):
    """Останавливает загрузку канала."""
    _, _, get_download_status, set_download_status, _ = get_download_globals()
    
    current_status = get_download_status(channel_id)
    
    if not current_status:
        return jsonify({"error": "Загрузка не найдена"}), 404
    
    if current_status.get('status') != 'downloading':
        return jsonify({"error": f"Загрузка уже завершена или остановлена. Текущий статус: {current_status.get('status')}"}), 400
    
    set_download_status(channel_id, 'stopped', {
        'message': 'Загрузка остановлена пользователем',
        'stopped_at': time.time()
    })
    
    return jsonify({"message": f"Загрузка канала {channel_id} остановлена"}), 200

@downloads_bp.route('/download/cancel/<channel_id>', methods=['POST'])
def cancel_download(channel_id):
    """Отменяет и очищает статус загрузки канала."""
    download_status, download_lock, _, _, _ = get_download_globals()
    
    with download_lock:
        if channel_id in download_status:
            del download_status[channel_id]
            return jsonify({"message": f"Статус загрузки канала {channel_id} очищен"}), 200
        else:
            return jsonify({"error": "Загрузка не найдена"}), 404

@downloads_bp.route('/download/clear/<channel_id>', methods=['POST'])
def clear_download_status(channel_id):
    """Очищает статус загрузки канала."""
    download_status, download_lock, _, _, _ = get_download_globals()
    
    with download_lock:
        if channel_id in download_status:
            del download_status[channel_id]
            return jsonify({"message": f"Статус загрузки канала {channel_id} очищен"}), 200
        else:
            return jsonify({"error": "Статус загрузки не найден"}), 404
