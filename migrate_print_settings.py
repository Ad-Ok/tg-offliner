#!/usr/bin/env python
"""
Миграция: добавление колонки print_settings в таблицы posts и channels
"""

import sqlite3
import os
import sys

DB_PATH = 'instance/posts.db'

def migrate():
    """Добавляет колонку print_settings в существующие таблицы"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        sys.exit(1)
    
    print(f"📦 Подключение к базе данных: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже колонка в posts
        cursor.execute("PRAGMA table_info(posts)")
        posts_columns = [col[1] for col in cursor.fetchall()]
        
        if 'print_settings' not in posts_columns:
            print("➕ Добавление колонки print_settings в таблицу posts...")
            cursor.execute("ALTER TABLE posts ADD COLUMN print_settings TEXT")
            print("✅ Колонка print_settings добавлена в posts")
        else:
            print("ℹ️  Колонка print_settings уже существует в posts")
        
        # Проверяем, есть ли уже колонка в channels
        cursor.execute("PRAGMA table_info(channels)")
        channels_columns = [col[1] for col in cursor.fetchall()]
        
        if 'print_settings' not in channels_columns:
            print("➕ Добавление колонки print_settings в таблицу channels...")
            cursor.execute("ALTER TABLE channels ADD COLUMN print_settings TEXT")
            print("✅ Колонка print_settings добавлена в channels")
        else:
            print("ℹ️  Колонка print_settings уже существует в channels")
        
        conn.commit()
        print("\n✅ Миграция успешно выполнена!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка миграции: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
