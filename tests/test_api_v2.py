"""
Тесты для API v2

Запуск: python -m pytest tests/test_api_v2.py -v
"""

import pytest
import json
from database import create_app, init_db
from models import db, Post, Channel, Layout, Edit
from api.v2 import api_v2_bp


@pytest.fixture
def app():
    """Создаёт тестовое приложение"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # Регистрируем API v2 blueprint
    app.register_blueprint(api_v2_bp)
    
    with app.app_context():
        init_db(app)
        db.create_all()
        
        # Создаём тестовый канал
        channel = Channel(
            id='test_channel',
            name='Test Channel',
            avatar=None,
            description='Test description',
            changes={'sortOrder': 'desc'},
            print_settings={'items_per_chunk': 50, 'page_size': 'A4'}
        )
        db.session.add(channel)
        
        # Создаём тестовые посты
        for i in range(10):
            post = Post(
                telegram_id=100 + i,
                channel_id='test_channel',
                date=f'2025-12-{25-i:02d}T12:00:00',
                message=f'Test post {i}',
                media_type='MessageMediaPhoto' if i % 3 == 0 else None
            )
            db.session.add(post)
        
        # Создаём пост с grouped_id (галерея)
        for i in range(3):
            post = Post(
                telegram_id=200 + i,
                channel_id='test_channel',
                date='2025-12-20T12:00:00',
                message='Gallery post' if i == 0 else None,
                media_type='MessageMediaPhoto',
                grouped_id=999
            )
            db.session.add(post)
        
        # Создаём layout для галереи
        layout = Layout(
            grouped_id=999,
            channel_id='test_channel',
            json_data={
                'cells': [
                    {'x': 0, 'y': 0, 'width': 50, 'height': 50, 'image_index': 0},
                    {'x': 50, 'y': 0, 'width': 50, 'height': 50, 'image_index': 1},
                    {'x': 0, 'y': 50, 'width': 100, 'height': 50, 'image_index': 2}
                ],
                'total_width': 100,
                'total_height': 100,
                'border_width': '2'
            }
        )
        db.session.add(layout)
        
        # Создаём скрытый пост
        edit = Edit(
            telegram_id=105,
            channel_id='test_channel',
            date='2025-12-25T12:00:00',
            changes={'hidden': 'true'}
        )
        db.session.add(edit)
        
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Создаёт тестовый клиент"""
    return app.test_client()


class TestGetChannelPosts:
    """Тесты для GET /api/v2/channels/{channel_id}/posts"""
    
    def test_get_posts_success(self, client):
        """Посты успешно загружаются"""
        response = client.get('/api/v2/channels/test_channel/posts')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'channel' in data
        assert 'pagination' in data
        assert 'applied_params' in data
        assert 'posts' in data
        
        assert data['channel']['id'] == 'test_channel'
        assert len(data['posts']) > 0
    
    def test_get_posts_channel_not_found(self, client):
        """404 если канал не найден"""
        response = client.get('/api/v2/channels/nonexistent/posts')
        
        assert response.status_code == 404
    
    def test_get_posts_default_sort_order(self, client):
        """По умолчанию используется сохранённый sort_order"""
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        assert data['applied_params']['sort_order'] == 'desc'
        assert data['applied_params']['source'] in ['saved', 'default']
    
    def test_get_posts_url_sort_override(self, client):
        """URL параметр имеет приоритет над сохранённым"""
        response = client.get('/api/v2/channels/test_channel/posts?sort_order=asc')
        data = response.get_json()
        
        assert data['applied_params']['sort_order'] == 'asc'
        assert data['applied_params']['source'] == 'url'
    
    def test_get_posts_with_chunk(self, client):
        """Chunking работает"""
        response = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=5')
        data = response.get_json()
        
        assert data['pagination']['current_chunk'] == 0
        assert data['pagination']['items_per_chunk'] == 5
    
    def test_get_posts_chunk_not_found(self, client):
        """404 если chunk не существует"""
        response = client.get('/api/v2/channels/test_channel/posts?chunk=999')
        
        assert response.status_code == 404
    
    def test_get_posts_hidden_excluded_by_default(self, client):
        """Скрытые посты исключаются по умолчанию"""
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        # Пост 105 скрыт
        telegram_ids = [p['telegram_id'] for p in data['posts']]
        assert 105 not in telegram_ids
    
    def test_get_posts_include_hidden(self, client):
        """Скрытые посты включаются при include_hidden=true"""
        response = client.get('/api/v2/channels/test_channel/posts?include_hidden=true')
        data = response.get_json()
        
        # Пост 105 должен быть включён
        post_105 = next((p for p in data['posts'] if p['telegram_id'] == 105), None)
        assert post_105 is not None
        assert post_105['is_hidden'] == True
    
    def test_get_posts_include_layout(self, client):
        """Посты с grouped_id включают layout"""
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        # Ищем пост с grouped_id=999
        gallery_post = next((p for p in data['posts'] if p.get('grouped_id') == 999), None)
        
        assert gallery_post is not None
        assert gallery_post['layout'] is not None
        assert 'cells' in gallery_post['layout']
        assert gallery_post['layout']['border_width'] == '2'
    
    def test_get_posts_group_posts_included(self, client):
        """Медиа-группы включают group_posts"""
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        gallery_post = next((p for p in data['posts'] if p.get('grouped_id') == 999), None)
        
        assert gallery_post is not None
        assert 'group_posts' in gallery_post
        assert len(gallery_post['group_posts']) == 3


class TestUpdateChannelSettings:
    """Тесты для PUT /api/v2/channels/{channel_id}/settings"""
    
    def test_update_settings_success(self, client):
        """Настройки успешно обновляются"""
        response = client.put(
            '/api/v2/channels/test_channel/settings',
            data=json.dumps({
                'display': {'sort_order': 'asc'}
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] == True
        assert data['settings']['display']['sort_order'] == 'asc'
    
    def test_update_settings_persists(self, client):
        """Изменения сохраняются в БД"""
        # Обновляем
        client.put(
            '/api/v2/channels/test_channel/settings',
            data=json.dumps({
                'display': {'sort_order': 'asc'}
            }),
            content_type='application/json'
        )
        
        # Проверяем что сохранилось
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        assert data['applied_params']['sort_order'] == 'asc'
        assert data['applied_params']['source'] == 'saved'
    
    def test_update_settings_channel_not_found(self, client):
        """404 если канал не найден"""
        response = client.put(
            '/api/v2/channels/nonexistent/settings',
            data=json.dumps({'display': {'sort_order': 'asc'}}),
            content_type='application/json'
        )
        
        assert response.status_code == 404


class TestPostVisibility:
    """Тесты для POST /api/v2/posts/{channel_id}/{telegram_id}/visibility"""
    
    def test_hide_post_success(self, client):
        """Пост успешно скрывается"""
        response = client.post(
            '/api/v2/posts/test_channel/100/visibility',
            data=json.dumps({'hidden': True}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['success'] == True
        assert data['hidden'] == True
    
    def test_hide_post_excludes_from_list(self, client):
        """Скрытый пост исключается из списка"""
        # Скрываем пост
        client.post(
            '/api/v2/posts/test_channel/100/visibility',
            data=json.dumps({'hidden': True}),
            content_type='application/json'
        )
        
        # Проверяем что исключён
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        telegram_ids = [p['telegram_id'] for p in data['posts']]
        assert 100 not in telegram_ids
    
    def test_unhide_post_success(self, client):
        """Пост успешно показывается"""
        # Пост 105 уже скрыт
        response = client.post(
            '/api/v2/posts/test_channel/105/visibility',
            data=json.dumps({'hidden': False}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Проверяем что теперь виден
        response = client.get('/api/v2/channels/test_channel/posts')
        data = response.get_json()
        
        telegram_ids = [p['telegram_id'] for p in data['posts']]
        assert 105 in telegram_ids
    
    def test_hide_post_not_found(self, client):
        """404 если пост не найден"""
        response = client.post(
            '/api/v2/posts/test_channel/99999/visibility',
            data=json.dumps({'hidden': True}),
            content_type='application/json'
        )
        
        assert response.status_code == 404


class TestGetChannelChunks:
    """Тесты для GET /api/v2/channels/{channel_id}/chunks"""
    
    def test_get_chunks_success(self, client):
        """Chunks metadata успешно возвращается"""
        response = client.get('/api/v2/channels/test_channel/chunks')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'channel_id' in data
        assert 'total_chunks' in data
        assert 'chunks' in data
        assert data['total_chunks'] >= 1
    
    def test_get_chunks_with_custom_size(self, client):
        """Chunks с кастомным размером"""
        response = client.get('/api/v2/channels/test_channel/chunks?items_per_chunk=5')
        data = response.get_json()
        
        assert data['items_per_chunk'] == 5
        # С 13 постами и размером 5 должно быть минимум 2 chunks
        assert data['total_chunks'] >= 2
