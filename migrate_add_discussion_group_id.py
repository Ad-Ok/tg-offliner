#!/usr/bin/env python3
"""
Скрипт миграции для добавления поля discussion_group_id в таблицу channels
"""

import sqlite3
import os

def add_discussion_group_id_column():
    # Путь к базе данных
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'posts.db')
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена по пути: {db_path}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже поле discussion_group_id
        cursor.execute("PRAGMA table_info(channels)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'discussion_group_id' in columns:
            print("Поле discussion_group_id уже существует в таблице channels")
            return True
        
        # Добавляем новое поле
        cursor.execute("""
            ALTER TABLE channels 
            ADD COLUMN discussion_group_id BIGINT
        """)
        
        conn.commit()
        print("Поле discussion_group_id успешно добавлено в таблицу channels")
        return True
        
    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Запуск миграции: добавление поля discussion_group_id в таблицу channels")
    success = add_discussion_group_id_column()
    if success:
        print("Миграция завершена успешно!")
    else:
        print("Миграция завершена с ошибками!")
