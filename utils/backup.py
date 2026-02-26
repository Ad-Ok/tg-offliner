"""
Утилиты для создания и восстановления бэкапов SQLite базы данных.

Использование:
    from utils.backup import create_backup, restore_backup, list_backups, delete_backup

Бэкапы хранятся в instance/backups/ в формате posts_YYYY-MM-DD_HH-MM-SS.db
"""

import os
import sqlite3
import shutil
from datetime import datetime

# Пути
INSTANCE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'posts.db')
BACKUP_DIR = os.path.join(INSTANCE_DIR, 'backups')

# Максимальное количество автобэкапов (ротация)
MAX_AUTO_BACKUPS = 10


def _ensure_backup_dir():
    """Создаёт папку для бэкапов если не существует"""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def create_backup(label=None):
    """
    Создаёт атомарный бэкап базы данных через sqlite3.Connection.backup().
    
    Args:
        label: Опциональная метка (добавляется к имени файла)
        
    Returns:
        dict: Информация о созданном бэкапе
            {name, path, size, created_at}
    """
    _ensure_backup_dir()
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    if label:
        filename = f'posts_{timestamp}_{label}.db'
    else:
        filename = f'posts_{timestamp}.db'
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    # Атомарная копия через sqlite3 backup API
    source = sqlite3.connect(DB_PATH)
    dest = sqlite3.connect(backup_path)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()
    
    size = os.path.getsize(backup_path)
    
    return {
        'name': filename,
        'path': backup_path,
        'size': size,
        'created_at': datetime.now().isoformat()
    }


def restore_backup(backup_name):
    """
    Восстанавливает базу из бэкапа.
    Перед восстановлением автоматически создаёт safety-бэкап.
    
    Args:
        backup_name: Имя файла бэкапа
        
    Returns:
        dict: {success, message, safety_backup}
        
    Raises:
        FileNotFoundError: Если бэкап не найден
        ValueError: Если бэкап повреждён
    """
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f'Бэкап {backup_name} не найден')
    
    # Валидация бэкапа
    _validate_backup(backup_path)
    
    # Safety бэкап текущего состояния
    safety = create_backup(label='before-restore')
    
    # Восстанавливаем через sqlite3 backup API
    source = sqlite3.connect(backup_path)
    dest = sqlite3.connect(DB_PATH)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()
    
    return {
        'success': True,
        'message': f'База восстановлена из {backup_name}',
        'safety_backup': safety['name']
    }


def _validate_backup(backup_path):
    """
    Проверяет целостность и структуру бэкапа.
    
    Raises:
        ValueError: Если бэкап невалиден
    """
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        
        # Проверка целостности
        cursor.execute('PRAGMA integrity_check')
        result = cursor.fetchone()
        if result[0] != 'ok':
            raise ValueError(f'Бэкап повреждён: {result[0]}')
        
        # Проверка наличия ключевых таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required = {'posts', 'channels'}
        missing = required - tables
        if missing:
            raise ValueError(f'В бэкапе отсутствуют таблицы: {", ".join(missing)}')
        
        conn.close()
    except sqlite3.Error as e:
        raise ValueError(f'Ошибка чтения бэкапа: {e}')


def list_backups():
    """
    Возвращает список бэкапов, отсортированный по дате (новые первыми).
    
    Returns:
        list[dict]: [{name, size, created_at, tables, rows}]
    """
    _ensure_backup_dir()
    
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if not filename.endswith('.db'):
            continue
        
        filepath = os.path.join(BACKUP_DIR, filename)
        stat = os.stat(filepath)
        
        # Получаем статистику из бэкапа
        stats = _get_backup_stats(filepath)
        
        backups.append({
            'name': filename,
            'size': stat.st_size,
            'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            **stats
        })
    
    # Сортируем: новые первыми
    backups.sort(key=lambda b: b['created_at'], reverse=True)
    
    return backups


def _get_backup_stats(filepath):
    """Получает количество записей в каждой таблице бэкапа"""
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        rows = {}
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                rows[table] = cursor.fetchone()[0]
            except sqlite3.Error:
                rows[table] = -1
        
        conn.close()
        return {'tables': tables, 'rows': rows}
    except sqlite3.Error:
        return {'tables': [], 'rows': {}}


def delete_backup(backup_name):
    """
    Удаляет бэкап.
    
    Args:
        backup_name: Имя файла бэкапа
        
    Raises:
        FileNotFoundError: Если бэкап не найден
    """
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f'Бэкап {backup_name} не найден')
    
    os.remove(backup_path)


def rotate_backups(max_count=MAX_AUTO_BACKUPS):
    """
    Удаляет старые автобэкапы, оставляя max_count самых новых.
    НЕ удаляет бэкапы с меткой 'before-restore' (safety).
    
    Args:
        max_count: Максимальное количество бэкапов
        
    Returns:
        int: Количество удалённых бэкапов
    """
    _ensure_backup_dir()
    
    backups = []
    for filename in sorted(os.listdir(BACKUP_DIR)):
        if not filename.endswith('.db'):
            continue
        # Не трогаем safety-бэкапы
        if 'before-restore' in filename:
            continue
        backups.append(filename)
    
    # Сортируем по имени (содержит timestamp) — старые первыми
    backups.sort()
    
    deleted = 0
    while len(backups) > max_count:
        oldest = backups.pop(0)
        os.remove(os.path.join(BACKUP_DIR, oldest))
        deleted += 1
    
    return deleted


def auto_backup():
    """
    Создаёт автоматический бэкап при старте приложения.
    Вызывается из start.sh.
    """
    # Проверяем что БД существует и не пустая
    if not os.path.exists(DB_PATH):
        print('⏭️  БД не найдена, бэкап не нужен')
        return
    
    size = os.path.getsize(DB_PATH)
    if size < 8192:  # Меньше 2 страниц — пустая БД
        print('⏭️  БД пустая, бэкап не нужен')
        return
    
    # Проверяем что есть таблицы с данными
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        if not tables:
            print('⏭️  БД без таблиц, бэкап не нужен')
            conn.close()
            return
        
        # Проверяем что есть хотя бы один канал
        cursor.execute('SELECT COUNT(*) FROM channels')
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print('⏭️  Нет каналов в БД, бэкап не нужен')
            return
    except sqlite3.Error:
        print('⚠️  Ошибка чтения БД, пропускаем бэкап')
        return
    
    backup = create_backup(label='auto')
    deleted = rotate_backups()
    
    print(f'✅ Автобэкап создан: {backup["name"]} ({backup["size"]} bytes)')
    if deleted:
        print(f'🗑️  Удалено старых бэкапов: {deleted}')


if __name__ == '__main__':
    auto_backup()
