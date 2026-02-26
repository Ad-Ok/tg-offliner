"""
Тесты для системы бэкапов

Запуск: docker compose exec app python -m pytest tests/test_backup.py -v
"""

import os
import sys
import json
import sqlite3
import shutil
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from models import db, Post, Channel, Edit, Layout, Page


class BackupUtilTests(unittest.TestCase):
    """Unit тесты для utils/backup.py"""

    def setUp(self):
        """Создаём временную директорию и тестовую БД"""
        self.temp_dir = tempfile.mkdtemp()
        self.instance_dir = os.path.join(self.temp_dir, 'instance')
        self.backup_dir = os.path.join(self.instance_dir, 'backups')
        self.db_path = os.path.join(self.instance_dir, 'posts.db')
        os.makedirs(self.instance_dir)

        # Создаём тестовую БД с данными
        self._create_test_db()

        # Патчим пути в модуле backup
        self.patches = [
            mock.patch('utils.backup.INSTANCE_DIR', self.instance_dir),
            mock.patch('utils.backup.DB_PATH', self.db_path),
            mock.patch('utils.backup.BACKUP_DIR', self.backup_dir),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.temp_dir)

    def _create_test_db(self):
        """Создаёт тестовую БД с таблицами и данными"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE channels (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            avatar TEXT, description TEXT, 
            creation_date TEXT, subscribers TEXT,
            posts_count INTEGER, comments_count INTEGER,
            discussion_group_id INTEGER,
            changes TEXT DEFAULT '{}',
            print_settings TEXT)''')
        c.execute('''CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            date TEXT NOT NULL,
            message TEXT)''')
        # Вставляем данные
        c.execute("INSERT INTO channels (id, name, changes) VALUES ('test', 'Test Channel', '{}')")
        c.execute("INSERT INTO channels (id, name, changes) VALUES ('test2', 'Test 2', '{}')")
        for i in range(10):
            c.execute("INSERT INTO posts (telegram_id, channel_id, date, message) VALUES (?, 'test', '2025-01-01', ?)",
                      (i + 1, f'Post {i + 1}'))
        conn.commit()
        conn.close()

    # ============ create_backup ============

    def test_create_backup_success(self):
        """Бэкап создаётся успешно"""
        from utils.backup import create_backup

        result = create_backup()

        self.assertIn('name', result)
        self.assertIn('size', result)
        self.assertTrue(result['name'].startswith('posts_'))
        self.assertTrue(result['name'].endswith('.db'))
        self.assertTrue(os.path.exists(result['path']))
        self.assertGreater(result['size'], 0)

    def test_create_backup_with_label(self):
        """Бэкап с меткой"""
        from utils.backup import create_backup

        result = create_backup(label='manual')

        self.assertIn('manual', result['name'])

    def test_create_backup_data_integrity(self):
        """Бэкап содержит все данные из исходной БД"""
        from utils.backup import create_backup

        result = create_backup()

        conn = sqlite3.connect(result['path'])
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM channels")
        self.assertEqual(c.fetchone()[0], 2)
        c.execute("SELECT COUNT(*) FROM posts")
        self.assertEqual(c.fetchone()[0], 10)
        conn.close()

    def test_create_backup_creates_dir(self):
        """create_backup создаёт папку backups если её нет"""
        from utils.backup import create_backup

        self.assertFalse(os.path.exists(self.backup_dir))
        create_backup()
        self.assertTrue(os.path.exists(self.backup_dir))

    # ============ list_backups ============

    def test_list_backups_empty(self):
        """Пустой список если нет бэкапов"""
        from utils.backup import list_backups

        result = list_backups()
        self.assertEqual(result, [])

    def test_list_backups_returns_all(self):
        """Возвращает все бэкапы"""
        from utils.backup import create_backup, list_backups

        create_backup(label='first')
        create_backup(label='second')

        result = list_backups()
        self.assertEqual(len(result), 2)

    def test_list_backups_sorted_newest_first(self):
        """Бэкапы отсортированы по дате (новые первыми)"""
        from utils.backup import create_backup, list_backups
        import time

        create_backup(label='old')
        time.sleep(0.1)
        create_backup(label='new')

        result = list_backups()
        self.assertIn('new', result[0]['name'])
        self.assertIn('old', result[1]['name'])

    def test_list_backups_includes_stats(self):
        """Бэкапы содержат статистику таблиц"""
        from utils.backup import create_backup, list_backups

        create_backup()
        result = list_backups()

        self.assertIn('tables', result[0])
        self.assertIn('rows', result[0])
        self.assertEqual(result[0]['rows']['channels'], 2)
        self.assertEqual(result[0]['rows']['posts'], 10)

    # ============ restore_backup ============

    def test_restore_backup_success(self):
        """Восстановление из бэкапа работает"""
        from utils.backup import create_backup, restore_backup

        backup = create_backup()

        # Портим текущую БД
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM posts")
        conn.commit()
        conn.close()

        # Восстанавливаем
        result = restore_backup(backup['name'])

        self.assertTrue(result['success'])
        self.assertIn('safety_backup', result)

        # Проверяем что данные вернулись
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM posts")
        self.assertEqual(c.fetchone()[0], 10)
        conn.close()

    def test_restore_creates_safety_backup(self):
        """При восстановлении создаётся safety-бэкап"""
        from utils.backup import create_backup, restore_backup, list_backups

        backup = create_backup()
        result = restore_backup(backup['name'])

        safety_name = result['safety_backup']
        self.assertIn('before-restore', safety_name)

        backups = list_backups()
        names = [b['name'] for b in backups]
        self.assertIn(safety_name, names)

    def test_restore_nonexistent_backup(self):
        """FileNotFoundError если бэкап не найден"""
        from utils.backup import restore_backup

        with self.assertRaises(FileNotFoundError):
            restore_backup('nonexistent.db')

    def test_restore_corrupted_backup(self):
        """ValueError если бэкап повреждён"""
        from utils.backup import restore_backup

        os.makedirs(self.backup_dir, exist_ok=True)
        bad_path = os.path.join(self.backup_dir, 'bad.db')
        with open(bad_path, 'w') as f:
            f.write('not a database')

        with self.assertRaises(ValueError):
            restore_backup('bad.db')

    def test_restore_backup_without_required_tables(self):
        """ValueError если в бэкапе нет нужных таблиц"""
        from utils.backup import restore_backup

        os.makedirs(self.backup_dir, exist_ok=True)
        empty_path = os.path.join(self.backup_dir, 'empty.db')
        conn = sqlite3.connect(empty_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        with self.assertRaises(ValueError):
            restore_backup('empty.db')

    # ============ delete_backup ============

    def test_delete_backup_success(self):
        """Бэкап удаляется"""
        from utils.backup import create_backup, delete_backup, list_backups

        backup = create_backup()
        delete_backup(backup['name'])

        self.assertEqual(len(list_backups()), 0)
        self.assertFalse(os.path.exists(backup['path']))

    def test_delete_nonexistent_backup(self):
        """FileNotFoundError если бэкап не найден"""
        from utils.backup import delete_backup

        with self.assertRaises(FileNotFoundError):
            delete_backup('nonexistent.db')

    # ============ rotate_backups ============

    def test_rotate_keeps_max_count(self):
        """Ротация оставляет только max_count бэкапов"""
        from utils.backup import create_backup, rotate_backups, list_backups
        import time

        for i in range(7):
            create_backup(label=f'test{i}')
            time.sleep(0.05)

        deleted = rotate_backups(max_count=3)

        self.assertEqual(deleted, 4)
        remaining = list_backups()
        self.assertEqual(len(remaining), 3)

    def test_rotate_preserves_safety_backups(self):
        """Ротация не удаляет safety-бэкапы (before-restore)"""
        from utils.backup import create_backup, rotate_backups, list_backups
        import time

        for i in range(5):
            create_backup(label=f'test{i}')
            time.sleep(0.05)
        create_backup(label='before-restore')

        rotate_backups(max_count=2)

        remaining = list_backups()
        safety = [b for b in remaining if 'before-restore' in b['name']]
        self.assertEqual(len(safety), 1)

    # ============ auto_backup ============

    def test_auto_backup_creates_backup(self):
        """auto_backup создаёт бэкап при наличии данных"""
        from utils.backup import auto_backup, list_backups

        auto_backup()

        backups = list_backups()
        self.assertEqual(len(backups), 1)
        self.assertIn('auto', backups[0]['name'])

    def test_auto_backup_skips_empty_db(self):
        """auto_backup не создаёт бэкап для пустой БД"""
        from utils.backup import auto_backup, list_backups

        # Очищаем каналы
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM channels")
        conn.commit()
        conn.close()

        auto_backup()

        self.assertEqual(len(list_backups()), 0)

    def test_auto_backup_skips_missing_db(self):
        """auto_backup не падает если БД не существует"""
        from utils.backup import auto_backup, list_backups

        os.remove(self.db_path)
        auto_backup()  # Не должен падать
        self.assertEqual(len(list_backups()), 0)


class BackupAPITests(unittest.TestCase):
    """Тесты для API endpoints бэкапов"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.instance_dir = os.path.join(self.temp_dir, 'instance')
        self.backup_dir = os.path.join(self.instance_dir, 'backups')
        self.db_path = os.path.join(self.instance_dir, 'posts.db')
        os.makedirs(self.instance_dir)

        # Создаём тестовую БД
        self._create_test_db()

        # Патчим пути
        self.patches = [
            mock.patch('utils.backup.INSTANCE_DIR', self.instance_dir),
            mock.patch('utils.backup.DB_PATH', self.db_path),
            mock.patch('utils.backup.BACKUP_DIR', self.backup_dir),
        ]
        for p in self.patches:
            p.start()

        # Создаём Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)

        from api.backup import backup_bp
        self.app.register_blueprint(backup_bp, url_prefix='/api')

        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.temp_dir)

    def _create_test_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE channels (
            id TEXT PRIMARY KEY, name TEXT NOT NULL,
            avatar TEXT, description TEXT,
            creation_date TEXT, subscribers TEXT,
            posts_count INTEGER, comments_count INTEGER,
            discussion_group_id INTEGER,
            changes TEXT DEFAULT '{}',
            print_settings TEXT)''')
        c.execute('''CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            date TEXT NOT NULL,
            message TEXT)''')
        c.execute("INSERT INTO channels (id, name, changes) VALUES ('test', 'Test', '{}')")
        for i in range(5):
            c.execute("INSERT INTO posts (telegram_id, channel_id, date, message) VALUES (?, 'test', '2025-01-01', ?)",
                      (i + 1, f'Post {i + 1}'))
        conn.commit()
        conn.close()

    # ============ GET /api/backups ============

    def test_get_backups_empty(self):
        """GET /api/backups — пустой список"""
        response = self.client.get('/api/backups')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['backups'], [])
        self.assertEqual(data['total'], 0)

    def test_get_backups_with_data(self):
        """GET /api/backups — со списком бэкапов"""
        from utils.backup import create_backup
        create_backup(label='test1')
        create_backup(label='test2')

        response = self.client.get('/api/backups')
        data = response.get_json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['backups']), 2)

    # ============ POST /api/backups ============

    def test_create_backup_endpoint(self):
        """POST /api/backups — создание бэкапа"""
        response = self.client.post('/api/backups',
                                    data=json.dumps({'label': 'api-test'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('api-test', data['backup']['name'])

    def test_create_backup_default_label(self):
        """POST /api/backups — метка по умолчанию 'manual'"""
        response = self.client.post('/api/backups',
                                    content_type='application/json')
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('manual', data['backup']['name'])

    # ============ POST /api/backups/<name>/restore ============

    def test_restore_endpoint_success(self):
        """POST /api/backups/<name>/restore — успешное восстановление"""
        from utils.backup import create_backup
        backup = create_backup(label='for-restore')

        response = self.client.post(f'/api/backups/{backup["name"]}/restore')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('safety_backup', data)

    def test_restore_endpoint_not_found(self):
        """POST /api/backups/nonexistent/restore — 404"""
        response = self.client.post('/api/backups/nonexistent.db/restore')
        self.assertEqual(response.status_code, 404)

    def test_restore_endpoint_invalid_backup(self):
        """POST /api/backups/bad.db/restore — 400 для повреждённого"""
        os.makedirs(self.backup_dir, exist_ok=True)
        with open(os.path.join(self.backup_dir, 'bad.db'), 'w') as f:
            f.write('corrupt')

        response = self.client.post('/api/backups/bad.db/restore')
        self.assertEqual(response.status_code, 400)

    # ============ DELETE /api/backups/<name> ============

    def test_delete_endpoint_success(self):
        """DELETE /api/backups/<name> — удаление"""
        from utils.backup import create_backup
        backup = create_backup()

        response = self.client.delete(f'/api/backups/{backup["name"]}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    def test_delete_endpoint_not_found(self):
        """DELETE /api/backups/nonexistent — 404"""
        response = self.client.delete('/api/backups/nonexistent.db')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
