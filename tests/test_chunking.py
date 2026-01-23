"""
Тесты для модуля разбиения на chunks
"""
import os
import sys
import unittest
from datetime import datetime

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from models import db, Post, Channel, Edit


class ChunkingUnitTests(unittest.TestCase):
    """Unit тесты для utils/chunking.py"""
    
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(self.app)
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_channel(self, channel_id='test_channel', discussion_id=None):
        """Создает тестовый канал"""
        channel = Channel(
            id=channel_id,
            name='Test Channel',
            discussion_group_id=discussion_id,
            changes={}
        )
        db.session.add(channel)
        db.session.commit()
        return channel
    
    def _create_post(self, telegram_id, channel_id='test_channel', 
                     date='2025-01-01', grouped_id=None, reply_to=None, message='Test'):
        """Создает тестовый пост"""
        post = Post(
            telegram_id=telegram_id,
            channel_id=channel_id,
            date=date,
            message=message,
            grouped_id=grouped_id,
            reply_to=reply_to
        )
        db.session.add(post)
        db.session.commit()
        return post
    
    def _create_hidden_edit(self, telegram_id, channel_id='test_channel'):
        """Создает edit со скрытием поста"""
        edit = Edit(
            telegram_id=telegram_id,
            channel_id=channel_id,
            date=datetime.now().isoformat(),
            changes={'hidden': 'true'}
        )
        db.session.add(edit)
        db.session.commit()
        return edit
    
    # ============ TESTS FOR get_visible_posts ============
    
    def test_get_visible_posts_returns_all_visible(self):
        """Все посты без скрытых возвращаются"""
        with self.app.app_context():
            from utils.chunking import get_visible_posts
            
            self._create_channel()
            self._create_post(1, date='2025-01-01')
            self._create_post(2, date='2025-01-02')
            self._create_post(3, date='2025-01-03')
            
            visible = get_visible_posts('test_channel')
            
            self.assertEqual(len(visible), 3)
    
    def test_get_visible_posts_excludes_hidden(self):
        """Скрытые посты не попадают в visible"""
        with self.app.app_context():
            from utils.chunking import get_visible_posts
            
            self._create_channel()
            self._create_post(1)
            self._create_post(2)
            self._create_post(3)
            self._create_hidden_edit(2)  # Скрываем пост 2
            
            visible = get_visible_posts('test_channel')
            
            self.assertEqual(len(visible), 2)
            visible_ids = [p.telegram_id for p in visible]
            self.assertIn(1, visible_ids)
            self.assertIn(3, visible_ids)
            self.assertNotIn(2, visible_ids)
    
    def test_get_visible_posts_sorted_desc(self):
        """Посты отсортированы по дате (новые первыми)"""
        with self.app.app_context():
            from utils.chunking import get_visible_posts
            
            self._create_channel()
            self._create_post(1, date='2025-01-01')
            self._create_post(2, date='2025-01-03')
            self._create_post(3, date='2025-01-02')
            
            visible = get_visible_posts('test_channel')
            
            self.assertEqual(visible[0].telegram_id, 2)  # Самый новый
            self.assertEqual(visible[1].telegram_id, 3)
            self.assertEqual(visible[2].telegram_id, 1)  # Самый старый
    
    # ============ TESTS FOR get_comments_for_post ============
    
    def test_get_comments_for_post_returns_comments(self):
        """Комментарии привязываются к посту через reply_to"""
        with self.app.app_context():
            from utils.chunking import get_comments_for_post
            
            self._create_channel('channel', discussion_id=12345)
            self._create_post(100, 'channel')
            
            # Создаем комментарии в дискуссионной группе
            self._create_post(1, '12345', reply_to=100)
            self._create_post(2, '12345', reply_to=100)
            self._create_post(3, '12345', reply_to=999)  # К другому посту
            
            comments = get_comments_for_post(100, '12345')
            
            self.assertEqual(len(comments), 2)
    
    def test_get_comments_for_post_no_discussion(self):
        """Без дискуссионной группы возвращается пустой список"""
        with self.app.app_context():
            from utils.chunking import get_comments_for_post
            
            comments = get_comments_for_post(100, None)
            
            self.assertEqual(len(comments), 0)
    
    # ============ TESTS FOR build_content_units ============
    
    def test_build_content_units_single_posts(self):
        """Одиночные посты становятся отдельными units"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            self._create_post(1, date='2025-01-01')
            self._create_post(2, date='2025-01-02')
            self._create_post(3, date='2025-01-03')
            
            units = build_content_units('test_channel')
            
            self.assertEqual(len(units), 3)
            # Проверяем сортировку (новые первыми)
            self.assertEqual(units[0]['post'].telegram_id, 3)
            self.assertEqual(units[1]['post'].telegram_id, 2)
            self.assertEqual(units[2]['post'].telegram_id, 1)
    
    def test_build_content_units_weight_without_comments(self):
        """Вес поста без комментариев = 1"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            self._create_post(1)
            
            units = build_content_units('test_channel')
            
            self.assertEqual(units[0]['weight'], 1)
            self.assertFalse(units[0]['is_group'])
    
    def test_build_content_units_media_group(self):
        """Медиа-группа объединяется в один unit"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            # Медиа-группа из 4 фото
            self._create_post(1, grouped_id=12345, date='2025-01-01')
            self._create_post(2, grouped_id=12345, date='2025-01-01')
            self._create_post(3, grouped_id=12345, date='2025-01-01')
            self._create_post(4, grouped_id=12345, date='2025-01-01')
            # Одиночный пост
            self._create_post(5, date='2025-01-02')
            
            units = build_content_units('test_channel')
            
            self.assertEqual(len(units), 2)  # 1 группа + 1 одиночный
            
            group_unit = next(u for u in units if u['is_group'])
            self.assertEqual(len(group_unit['group_posts']), 4)
            self.assertEqual(group_unit['weight'], 4)  # 4 фото, 0 комментариев
    
    def test_build_content_units_with_comments(self):
        """Комментарии добавляются к weight"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel('channel', discussion_id=99999)
            self._create_post(100, 'channel')
            
            # 3 комментария
            self._create_post(1, '99999', reply_to=100)
            self._create_post(2, '99999', reply_to=100)
            self._create_post(3, '99999', reply_to=100)
            
            units = build_content_units('channel')
            
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0]['weight'], 4)  # 1 пост + 3 комментария
            self.assertEqual(len(units[0]['comments']), 3)
    
    def test_build_content_units_group_with_comments(self):
        """Медиа-группа с комментариями"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel('channel', discussion_id=99999)
            # Медиа-группа из 3 фото
            self._create_post(1, 'channel', grouped_id=12345)
            self._create_post(2, 'channel', grouped_id=12345)
            self._create_post(3, 'channel', grouped_id=12345)
            
            # 2 комментария к первому посту группы
            self._create_post(101, '99999', reply_to=1)
            self._create_post(102, '99999', reply_to=1)
            
            units = build_content_units('channel')
            
            self.assertEqual(len(units), 1)
            self.assertTrue(units[0]['is_group'])
            self.assertEqual(len(units[0]['group_posts']), 3)
            self.assertEqual(len(units[0]['comments']), 2)
            self.assertEqual(units[0]['weight'], 5)  # 3 фото + 2 комментария
    
    def test_build_content_units_empty_channel(self):
        """Пустой канал возвращает пустой список"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            
            units = build_content_units('test_channel')
            
            self.assertEqual(len(units), 0)
    
    def test_build_content_units_nonexistent_channel(self):
        """Несуществующий канал возвращает пустой список"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            units = build_content_units('nonexistent')
            
            self.assertEqual(len(units), 0)
    
    # ============ TESTS FOR calculate_chunks ============
    
    def test_calculate_chunks_simple(self):
        """Простое разбиение без комментариев"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel()
            # 10 постов
            for i in range(10):
                self._create_post(i, date=f'2025-01-{i+1:02d}')
            
            chunks = calculate_chunks('test_channel', items_per_chunk=3)
            
            self.assertEqual(len(chunks), 4)  # 10 постов / 3 = 4 chunks (3+3+3+1)
            self.assertEqual(chunks[0]['posts_count'], 3)
            self.assertEqual(chunks[1]['posts_count'], 3)
            self.assertEqual(chunks[2]['posts_count'], 3)
            self.assertEqual(chunks[3]['posts_count'], 1)
    
    def test_calculate_chunks_dates(self):
        """Даты chunk корректно определяются"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel()
            self._create_post(1, date='2025-01-01')
            self._create_post(2, date='2025-01-15')
            self._create_post(3, date='2025-01-30')
            
            chunks = calculate_chunks('test_channel', items_per_chunk=10)
            
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0]['date_from'], '2025-01-30')  # Самый новый
            self.assertEqual(chunks[0]['date_to'], '2025-01-01')    # Самый старый
    
    def test_calculate_chunks_respects_atomic_unit(self):
        """Пост с комментариями не разрывается"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # Пост 1: вес = 1
            self._create_post(1, 'channel', date='2025-01-01')
            
            # Пост 2: вес = 6 (1 + 5 комментариев)
            self._create_post(2, 'channel', date='2025-01-02')
            for i in range(5):
                self._create_post(100+i, '99999', reply_to=2)
            
            # items_per_chunk=5, overflow=0.2 → max=6
            # Пост 2 (вес 6) идет первым (новее)
            # Пост 1 (вес 1) → 6+1=7 > 6, chunk почти полный (6 >= 4)
            chunks = calculate_chunks('channel', items_per_chunk=5, overflow_threshold=0.2)
            
            # Должно быть 2 chunks
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]['total_weight'], 6)  # Пост 2 + 5 комментариев
            self.assertEqual(chunks[1]['total_weight'], 1)  # Пост 1
    
    def test_calculate_chunks_huge_unit_in_empty_chunk(self):
        """Огромный unit добавляется в пустой chunk"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # Пост с 20 комментариями (вес = 21)
            self._create_post(1, 'channel', date='2025-01-01')
            for i in range(20):
                self._create_post(100+i, '99999', reply_to=1)
            
            # items_per_chunk=5 → max=6, но unit = 21
            chunks = calculate_chunks('channel', items_per_chunk=5)
            
            # Один chunk с огромным unit
            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0]['total_weight'], 21)
    
    def test_calculate_chunks_empty_channel(self):
        """Пустой канал возвращает пустой список chunks"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel()
            
            chunks = calculate_chunks('test_channel')
            
            self.assertEqual(len(chunks), 0)
    
    # ============ TESTS FOR get_chunk_posts_and_comments ============
    
    def test_get_chunk_posts_and_comments(self):
        """Извлечение постов и комментариев из chunk"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks, get_chunk_posts_and_comments
            
            self._create_channel('channel', discussion_id=99999)
            
            self._create_post(1, 'channel', date='2025-01-01')
            self._create_post(2, 'channel', date='2025-01-02')
            self._create_post(101, '99999', reply_to=1)
            self._create_post(102, '99999', reply_to=2)
            
            chunks = calculate_chunks('channel', items_per_chunk=100)
            posts, comments = get_chunk_posts_and_comments(chunks[0])
            
            self.assertEqual(len(posts), 2)
            self.assertEqual(len(comments), 2)


class ChunksAPITests(unittest.TestCase):
    """Тесты для API chunks"""
    
    def setUp(self):
        # Создаем отдельное тестовое приложение с in-memory БД
        # НЕ импортируем app из app.py чтобы не затронуть production БД!
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(self.app)
        
        # Регистрируем blueprint для chunks API
        from api.chunks import chunks_bp
        self.app.register_blueprint(chunks_bp)
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Создаем тестовый канал
            channel = Channel(
                id='test_channel',
                name='Test Channel',
                changes={},
                print_settings={'items_per_chunk': 10}
            )
            db.session.add(channel)
            
            # Создаем 25 постов
            for i in range(25):
                post = Post(
                    telegram_id=i+1,
                    channel_id='test_channel',
                    date=f'2025-01-{i+1:02d}',
                    message=f'Post {i+1}'
                )
                db.session.add(post)
            
            db.session.commit()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_get_channel_chunks_success(self):
        """GET /api/chunks/<channel_id> возвращает информацию о chunks"""
        response = self.client.get('/api/chunks/test_channel')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['channel_id'], 'test_channel')
        self.assertEqual(data['items_per_chunk'], 10)
        self.assertGreater(data['total_chunks'], 0)
        self.assertEqual(data['total_posts'], 25)
        self.assertIn('chunks', data)
    
    def test_get_channel_chunks_not_found(self):
        """GET /api/chunks/<channel_id> для несуществующего канала"""
        response = self.client.get('/api/chunks/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_channel_chunks_with_custom_items_per_chunk(self):
        """GET /api/chunks/<channel_id>?items_per_chunk=5"""
        response = self.client.get('/api/chunks/test_channel?items_per_chunk=5')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['items_per_chunk'], 5)
        # С items_per_chunk=5 должно быть больше chunks
        self.assertGreater(data['total_chunks'], 3)
    
    def test_get_chunk_posts_success(self):
        """GET /api/chunks/<channel_id>/<index>/posts возвращает посты chunk"""
        response = self.client.get('/api/chunks/test_channel/0/posts')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['chunk_index'], 0)
        self.assertIn('posts', data)
        self.assertIn('comments', data)
        self.assertGreater(len(data['posts']), 0)
    
    def test_get_chunk_posts_invalid_index(self):
        """GET /api/chunks/<channel_id>/<index>/posts для несуществующего chunk"""
        response = self.client.get('/api/chunks/test_channel/999/posts')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_get_chunk_posts_channel_not_found(self):
        """GET /api/chunks/<channel_id>/<index>/posts для несуществующего канала"""
        response = self.client.get('/api/chunks/nonexistent/0/posts')
        
        self.assertEqual(response.status_code, 404)


class ChunkingIntegrationTests(unittest.TestCase):
    """Интеграционные тесты для сценариев из спецификации"""
    
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(self.app)
        
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_channel(self, channel_id='test_channel', discussion_id=None):
        channel = Channel(
            id=channel_id,
            name='Test Channel',
            discussion_group_id=discussion_id,
            changes={}
        )
        db.session.add(channel)
        db.session.commit()
        return channel
    
    def _create_post(self, telegram_id, channel_id='test_channel', 
                     date='2025-01-01', grouped_id=None, reply_to=None):
        post = Post(
            telegram_id=telegram_id,
            channel_id=channel_id,
            date=date,
            message=f'Post {telegram_id}',
            grouped_id=grouped_id,
            reply_to=reply_to
        )
        db.session.add(post)
        db.session.commit()
        return post
    
    def test_scenario_100_posts_no_comments(self):
        """Сценарий 1: 100 постов без комментариев"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel()
            
            # 100 постов
            for i in range(100):
                self._create_post(i+1, date=f'2025-{(i//28)+1:02d}-{(i%28)+1:02d}')
            
            chunks = calculate_chunks('test_channel', items_per_chunk=50)
            
            self.assertEqual(len(chunks), 2)
            # С overflow 20% первый chunk может содержать до 60 постов
            total_posts = sum(c['posts_count'] for c in chunks)
            self.assertEqual(total_posts, 100)
            self.assertEqual(chunks[0]['comments_count'], 0)
            self.assertEqual(chunks[1]['comments_count'], 0)
    
    def test_scenario_50_posts_with_comments(self):
        """Сценарий 2: 50 постов, 2-3 комментария в каждом"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # 50 постов с 2-3 комментариями каждый
            comment_id = 1000
            for i in range(50):
                self._create_post(i+1, 'channel', date=f'2025-01-{(i%28)+1:02d}')
                # 2-3 комментария
                num_comments = 2 + (i % 2)
                for j in range(num_comments):
                    self._create_post(comment_id, '99999', reply_to=i+1)
                    comment_id += 1
            
            chunks = calculate_chunks('channel', items_per_chunk=50)
            
            # С 50 постами и ~125 комментариями (вес ~175), 
            # должно получиться несколько chunks
            self.assertGreater(len(chunks), 1)
            
            # Проверяем, что комментарии не разрываются
            for chunk in chunks:
                # Каждый пост должен иметь все свои комментарии
                self.assertGreaterEqual(chunk['total_weight'], chunk['posts_count'])
    
    def test_scenario_2_posts_many_comments(self):
        """Сценарий 3: 2 поста по 100+ комментариев"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # Пост 1 с 150 комментариями
            self._create_post(1, 'channel', date='2025-01-01')
            for i in range(150):
                self._create_post(1000+i, '99999', reply_to=1)
            
            # Пост 2 с 120 комментариями
            self._create_post(2, 'channel', date='2025-01-02')
            for i in range(120):
                self._create_post(2000+i, '99999', reply_to=2)
            
            chunks = calculate_chunks('channel', items_per_chunk=50)
            
            # Каждый пост должен быть в своем chunk (они огромные)
            self.assertEqual(len(chunks), 2)
            
            # Проверяем, что посты не разорваны
            chunk_weights = [c['total_weight'] for c in chunks]
            self.assertIn(151, chunk_weights)  # 1 + 150
            self.assertIn(121, chunk_weights)  # 1 + 120


if __name__ == '__main__':
    unittest.main()
