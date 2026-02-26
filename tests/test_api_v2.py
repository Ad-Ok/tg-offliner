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
    app = create_app(database_uri='sqlite:///:memory:')
    app.config['TESTING'] = True
    
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
    
    def test_get_chunks_channel_not_found(self, client):
        """404 если канал не найден"""
        response = client.get('/api/v2/channels/nonexistent/chunks')
        assert response.status_code == 404
    
    def test_get_chunks_with_sort_order_asc(self, client):
        """Chunks с sort_order=asc"""
        response = client.get('/api/v2/channels/test_channel/chunks?sort_order=asc')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['sort_order'] == 'asc'
        assert data['total_chunks'] >= 1
        
        # Даты в чанках: первый chunk содержит старые посты
        if data['total_chunks'] > 1:
            first_chunk = data['chunks'][0]
            last_chunk = data['chunks'][-1]
            assert first_chunk['date_from'] <= last_chunk['date_from']
    
    def test_get_chunks_with_sort_order_desc(self, client):
        """Chunks с sort_order=desc возвращает новые посты первыми"""
        response = client.get('/api/v2/channels/test_channel/chunks?sort_order=desc')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['sort_order'] == 'desc'
        
        if data['total_chunks'] > 1:
            first_chunk = data['chunks'][0]
            last_chunk = data['chunks'][-1]
            assert first_chunk['date_from'] >= last_chunk['date_from']
    
    def test_get_chunks_metadata_shape(self, client):
        """Каждый chunk содержит все необходимые поля"""
        response = client.get('/api/v2/channels/test_channel/chunks?items_per_chunk=5')
        data = response.get_json()
        
        for chunk in data['chunks']:
            assert 'index' in chunk
            assert 'posts_count' in chunk
            assert 'comments_count' in chunk
            assert 'total_weight' in chunk
            assert 'date_from' in chunk
            assert 'date_to' in chunk
            assert chunk['posts_count'] > 0


class TestV2ChunkingEdgeCases:
    """Тесты для edge cases chunking через V2 API"""
    
    def test_chunk_boundary_posts_correct(self, client):
        """Посты в chunk 0 и chunk 1 не пересекаются"""
        response_0 = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=5')
        response_1 = client.get('/api/v2/channels/test_channel/posts?chunk=1&items_per_chunk=5')
        
        assert response_0.status_code == 200
        assert response_1.status_code == 200
        
        ids_0 = {p['telegram_id'] for p in response_0.get_json()['posts']}
        ids_1 = {p['telegram_id'] for p in response_1.get_json()['posts']}
        
        # Нет пересечения
        assert ids_0.isdisjoint(ids_1)
    
    def test_all_chunks_cover_all_posts(self, client):
        """Сумма постов по всем chunks = общее количество постов"""
        # Сначала получаем всё без chunking
        all_response = client.get('/api/v2/channels/test_channel/posts')
        all_ids = {p['telegram_id'] for p in all_response.get_json()['posts']}
        
        # Получаем метаданные chunks
        chunks_response = client.get('/api/v2/channels/test_channel/chunks?items_per_chunk=5')
        chunks_data = chunks_response.get_json()
        
        # Собираем все id из всех chunks
        chunked_ids = set()
        for i in range(chunks_data['total_chunks']):
            chunk_response = client.get(f'/api/v2/channels/test_channel/posts?chunk={i}&items_per_chunk=5')
            for p in chunk_response.get_json()['posts']:
                chunked_ids.add(p['telegram_id'])
        
        assert chunked_ids == all_ids
    
    def test_include_hidden_with_chunking(self, client):
        """include_hidden=true работает вместе с chunking"""
        # Без hidden
        response_no_hidden = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=50')
        ids_no_hidden = {p['telegram_id'] for p in response_no_hidden.get_json()['posts']}
        
        # С hidden
        response_hidden = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=50&include_hidden=true')
        data_hidden = response_hidden.get_json()
        ids_hidden = {p['telegram_id'] for p in data_hidden['posts']}
        
        # С include_hidden должно быть как минимум столько же постов
        assert len(ids_hidden) >= len(ids_no_hidden)
        
        # Пост 105 скрыт — должен быть в hidden-версии
        assert 105 in ids_hidden
        
        # Скрытый пост помечен is_hidden=True
        post_105 = next(p for p in data_hidden['posts'] if p['telegram_id'] == 105)
        assert post_105['is_hidden'] == True
    
    def test_include_comments_false_with_chunking(self, client):
        """include_comments=false убирает комментарии из ответа"""
        response = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=50&include_comments=false')
        data = response.get_json()
        
        assert response.status_code == 200
        # Все посты не должны иметь комментариев
        for post in data['posts']:
            assert post.get('comments', []) == []
    
    def test_chunk_pagination_metadata_consistent(self, client):
        """pagination metadata корректна при chunking"""
        response = client.get('/api/v2/channels/test_channel/posts?chunk=0&items_per_chunk=5')
        data = response.get_json()
        
        pag = data['pagination']
        assert pag['current_chunk'] == 0
        assert pag['items_per_chunk'] == 5
        assert pag['total_chunks'] >= 2
        assert pag['has_next'] == True
        assert pag['has_prev'] == False
        assert pag['total_posts'] > 0
    
    def test_last_chunk_has_prev_no_next(self, client):
        """Последний chunk имеет has_prev=True, has_next=False"""
        # Узнаём количество chunks
        chunks_resp = client.get('/api/v2/channels/test_channel/chunks?items_per_chunk=5')
        total = chunks_resp.get_json()['total_chunks']
        
        last_idx = total - 1
        response = client.get(f'/api/v2/channels/test_channel/posts?chunk={last_idx}&items_per_chunk=5')
        data = response.get_json()
        
        pag = data['pagination']
        assert pag['current_chunk'] == last_idx
        assert pag['has_next'] == False
        if total > 1:
            assert pag['has_prev'] == True
    
    def test_sort_order_affects_chunk_content(self, client):
        """Разные sort_order дают одинаковый набор постов но в разном порядке"""
        resp_desc = client.get('/api/v2/channels/test_channel/posts?sort_order=desc')
        resp_asc = client.get('/api/v2/channels/test_channel/posts?sort_order=asc')
        
        ids_desc = [p['telegram_id'] for p in resp_desc.get_json()['posts']]
        ids_asc = [p['telegram_id'] for p in resp_asc.get_json()['posts']]
        
        # Одинаковый набор
        assert set(ids_desc) == set(ids_asc)
        # Разный порядок
        assert ids_desc != ids_asc


class TestV2ChunkingEmptyChannel:
    """Тесты для V2 chunking с пустым каналом"""
    
    @pytest.fixture(autouse=True)
    def setup_empty_channel(self, app):
        """Добавляет пустой канал"""
        with app.app_context():
            empty_channel = Channel(
                id='empty_channel',
                name='Empty Channel',
                changes={},
                print_settings={}
            )
            db.session.add(empty_channel)
            db.session.commit()
    
    def test_chunks_empty_channel(self, client):
        """Пустой канал — 0 chunks"""
        response = client.get('/api/v2/channels/empty_channel/chunks')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['total_chunks'] == 0
        assert data['chunks'] == []
    
    def test_posts_empty_channel_no_chunk(self, client):
        """Пустой канал без chunk параметра — пустой список"""
        response = client.get('/api/v2/channels/empty_channel/posts')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['posts'] == []
        assert data['pagination']['total_posts'] == 0
    
    def test_posts_empty_channel_chunk_0_not_found(self, client):
        """Пустой канал с chunk=0 — 404"""
        response = client.get('/api/v2/channels/empty_channel/posts?chunk=0')
        assert response.status_code == 404


class TestV2ChunkingIntegrationScenarios:
    """
    Интеграционные сценарии из спецификации, протестированные через V2 HTTP API.
    Проверяют что chunking корректно работает end-to-end.
    """
    
    @pytest.fixture
    def big_channel_app(self):
        """Flask app со 100 постами для интеграционных сценариев"""
        app = create_app(database_uri='sqlite:///:memory:')
        app.config['TESTING'] = True
        
        app.register_blueprint(api_v2_bp)
        
        with app.app_context():
            init_db(app)
            db.create_all()
            
            channel = Channel(
                id='big_channel',
                name='Big Channel',
                changes={},
                print_settings={}
            )
            db.session.add(channel)
            
            for i in range(100):
                post = Post(
                    telegram_id=i + 1,
                    channel_id='big_channel',
                    date=f'2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}T12:00:00',
                    message=f'Post {i + 1}'
                )
                db.session.add(post)
            
            db.session.commit()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def big_client(self, big_channel_app):
        return big_channel_app.test_client()
    
    def test_scenario_100_posts_via_api(self, big_client):
        """Сценарий 1: 100 постов без комментариев через V2 API"""
        # Метаданные chunks
        chunks_resp = big_client.get('/api/v2/channels/big_channel/chunks?items_per_chunk=50')
        chunks_data = chunks_resp.get_json()
        
        assert chunks_resp.status_code == 200
        assert chunks_data['total_chunks'] == 2
        
        # Собираем все посты через chunks
        all_ids = set()
        for i in range(chunks_data['total_chunks']):
            resp = big_client.get(f'/api/v2/channels/big_channel/posts?chunk={i}&items_per_chunk=50')
            assert resp.status_code == 200
            data = resp.get_json()
            for p in data['posts']:
                all_ids.add(p['telegram_id'])
        
        assert len(all_ids) == 100
    
    @pytest.fixture
    def comments_channel_app(self):
        """Flask app с 50 постами и комментариями"""
        app = create_app(database_uri='sqlite:///:memory:')
        app.config['TESTING'] = True
        
        app.register_blueprint(api_v2_bp)
        
        with app.app_context():
            init_db(app)
            db.create_all()
            
            channel = Channel(
                id='comments_channel',
                name='Comments Channel',
                discussion_group_id=99999,
                changes={},
                print_settings={}
            )
            db.session.add(channel)
            
            comment_id = 1000
            for i in range(50):
                post = Post(
                    telegram_id=i + 1,
                    channel_id='comments_channel',
                    date=f'2025-01-{(i % 28) + 1:02d}T{i % 24:02d}:00:00',
                    message=f'Post {i + 1}'
                )
                db.session.add(post)
                
                num_comments = 2 + (i % 2)
                for j in range(num_comments):
                    comment = Post(
                        telegram_id=comment_id,
                        channel_id='99999',
                        date=f'2025-01-{(i % 28) + 1:02d}T{i % 24:02d}:30:00',
                        message=f'Comment {comment_id}',
                        reply_to=i + 1
                    )
                    db.session.add(comment)
                    comment_id += 1
            
            db.session.commit()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def comments_client(self, comments_channel_app):
        return comments_channel_app.test_client()
    
    def test_scenario_50_posts_with_comments_via_api(self, comments_client):
        """Сценарий 2: 50 постов с комментариями — комментарии не разрываются"""
        chunks_resp = comments_client.get('/api/v2/channels/comments_channel/chunks?items_per_chunk=50')
        chunks_data = chunks_resp.get_json()
        
        assert chunks_resp.status_code == 200
        # С 50 постами и ~125 комментариями (вес ~175), несколько chunks
        assert chunks_data['total_chunks'] > 1
        
        # Проверяем: каждый пост в каждом chunk имеет все свои комментарии
        for i in range(chunks_data['total_chunks']):
            resp = comments_client.get(
                f'/api/v2/channels/comments_channel/posts?chunk={i}&items_per_chunk=50&include_comments=true')
            data = resp.get_json()
            
            for post in data['posts']:
                comments = post.get('comments', [])
                # Каждый пост имеет 2 или 3 комментария (неразорванных)
                if comments:
                    assert len(comments) in [2, 3]
    
    @pytest.fixture
    def huge_comments_app(self):
        """Flask app с 2 постами по 100+ комментариев"""
        app = create_app(database_uri='sqlite:///:memory:')
        app.config['TESTING'] = True
        
        app.register_blueprint(api_v2_bp)
        
        with app.app_context():
            init_db(app)
            db.create_all()
            
            channel = Channel(
                id='huge_channel',
                name='Huge Channel',
                discussion_group_id=88888,
                changes={},
                print_settings={}
            )
            db.session.add(channel)
            
            # Пост 1 со 150 комментариями
            db.session.add(Post(
                telegram_id=1, channel_id='huge_channel',
                date='2025-01-01T12:00:00', message='Post 1'))
            for i in range(150):
                db.session.add(Post(
                    telegram_id=1000 + i, channel_id='88888',
                    date='2025-01-01T13:00:00', message=f'Comment {i}',
                    reply_to=1))
            
            # Пост 2 со 120 комментариями
            db.session.add(Post(
                telegram_id=2, channel_id='huge_channel',
                date='2025-01-02T12:00:00', message='Post 2'))
            for i in range(120):
                db.session.add(Post(
                    telegram_id=2000 + i, channel_id='88888',
                    date='2025-01-02T13:00:00', message=f'Comment {i}',
                    reply_to=2))
            
            db.session.commit()
            yield app
            db.session.remove()
            db.drop_all()
    
    @pytest.fixture
    def huge_client(self, huge_comments_app):
        return huge_comments_app.test_client()
    
    def test_scenario_huge_comments_via_api(self, huge_client):
        """Сценарий 3: 2 поста с 150/120 комментариями — каждый в своём chunk"""
        chunks_resp = huge_client.get('/api/v2/channels/huge_channel/chunks?items_per_chunk=50')
        chunks_data = chunks_resp.get_json()
        
        assert chunks_resp.status_code == 200
        assert chunks_data['total_chunks'] == 2
        
        # Каждый chunk содержит 1 пост со всеми комментариями
        weights = sorted([c['total_weight'] for c in chunks_data['chunks']])
        assert weights == [121, 151]
        
        # Проверяем содержимое chunk 0
        resp_0 = huge_client.get('/api/v2/channels/huge_channel/posts?chunk=0&items_per_chunk=50')
        data_0 = resp_0.get_json()
        assert len(data_0['posts']) == 1
        
        # Проверяем содержимое chunk 1
        resp_1 = huge_client.get('/api/v2/channels/huge_channel/posts?chunk=1&items_per_chunk=50')
        data_1 = resp_1.get_json()
        assert len(data_1['posts']) == 1
