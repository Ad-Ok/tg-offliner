import os
import sys
import unittest
from unittest import mock
from flask import Flask

# Ensure required environment variables exist before importing project modules
os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.layouts import layouts_bp
from models import db, Layout, Post


class LayoutsAPITests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(self.app)
        self.app.register_blueprint(layouts_bp, url_prefix='/api')

        with self.app.app_context():
            db.create_all()

        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @mock.patch('api.layouts.generate_gallery_layout')
    def test_get_layout_success(self, mock_generate):
        """Тест успешного получения layout"""
        with self.app.app_context():
            # Создаем тестовый layout
            layout = Layout(
                grouped_id='test_group_123',
                channel_id='test_channel_456',
                json_data={'total_width': 100, 'total_height': 200, 'cells': []}
            )
            db.session.add(layout)
            db.session.commit()

            response = self.client.get('/api/layouts/test_group_123?channel_id=test_channel_456')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['total_width'], 100)
            self.assertEqual(data['total_height'], 200)

    def test_get_layout_not_found(self):
        """Тест получения несуществующего layout"""
        response = self.client.get('/api/layouts/nonexistent?channel_id=test_channel')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('Layout not found', data['error'])

    def test_get_layout_missing_channel_id(self):
        """Тест получения layout без channel_id"""
        response = self.client.get('/api/layouts/test_group')
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('channel_id parameter is required', data['error'])

    @mock.patch('api.layouts._resolve_image_path')
    @mock.patch('api.layouts.generate_gallery_layout')
    def test_reload_layout_success(self, mock_generate, mock_resolve):
        """Тест успешной перегенерации layout"""
        mock_generate.return_value = {
            'total_width': 150,
            'total_height': 250,
            'image_count': 3,
            'cells': [{'image_index': 0, 'x': 0, 'y': 0, 'width': 50, 'height': 50}],
            'border_width': '5'
        }
        mock_resolve.return_value = '/tmp/test_image.jpg'  # Mock path

        with self.app.app_context():
            # Создаем тестовые посты
            post1 = Post(
                telegram_id=1,
                channel_id='test_channel_456',
                date='2023-01-01',
                grouped_id='test_group_123',
                media_type='MessageMediaPhoto',
                media_url='/media/test1.jpg'
            )
            post2 = Post(
                telegram_id=2,
                channel_id='test_channel_456',
                date='2023-01-01',
                grouped_id='test_group_123',
                media_type='MessageMediaPhoto',
                media_url='/media/test2.jpg'
            )
            db.session.add(post1)
            db.session.add(post2)
            db.session.commit()

            payload = {
                'channel_id': 'test_channel_456',
                'columns': 2,
                'no_crop': True,
                'border_width': '5'
            }
            response = self.client.post('/api/layouts/test_group_123/reload', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('layout', data)
            self.assertEqual(data['layout']['border_width'], '5')

            # Проверяем, что layout сохранен в БД
            layout = Layout.query.filter_by(grouped_id='test_group_123', channel_id='test_channel_456').first()
            self.assertIsNotNone(layout)
            self.assertEqual(layout.json_data['border_width'], '5')

    @mock.patch('api.layouts._resolve_image_path')
    def test_reload_layout_insufficient_images(self, mock_resolve):
        """Тест перегенерации layout с недостаточным количеством изображений"""
        mock_resolve.return_value = '/tmp/test_image.jpg'

        with self.app.app_context():
            # Создаем только один пост
            post = Post(
                telegram_id=1,
                channel_id='test_channel_456',
                date='2023-01-01',
                grouped_id='test_group_123',
                media_type='MessageMediaPhoto',
                media_url='/media/test1.jpg'
            )
            db.session.add(post)
            db.session.commit()

            payload = {'channel_id': 'test_channel_456'}
            response = self.client.post('/api/layouts/test_group_123/reload', json=payload)
            self.assertEqual(response.status_code, 400)
            data = response.get_json()
            self.assertIn('At least two images are required', data['error'])

    def test_reload_layout_missing_channel_id(self):
        """Тест перегенерации layout без channel_id"""
        response = self.client.post('/api/layouts/test_group_123/reload', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('channel_id parameter is required', data['error'])

    @mock.patch('api.layouts._resolve_image_path')
    @mock.patch('api.layouts.generate_gallery_layout')
    def test_reload_layout_generation_failed(self, mock_generate, mock_resolve):
        """Тест перегенерации layout при неудачной генерации"""
        mock_generate.return_value = None
        mock_resolve.return_value = '/tmp/test_image.jpg'

        with self.app.app_context():
            # Создаем тестовые посты
            post1 = Post(
                telegram_id=1,
                channel_id='test_channel_456',
                date='2023-01-01',
                grouped_id='test_group_123',
                media_type='MessageMediaPhoto',
                media_url='/media/test1.jpg'
            )
            post2 = Post(
                telegram_id=2,
                channel_id='test_channel_456',
                date='2023-01-01',
                grouped_id='test_group_123',
                media_type='MessageMediaPhoto',
                media_url='/media/test2.jpg'
            )
            db.session.add(post1)
            db.session.add(post2)
            db.session.commit()

            payload = {'channel_id': 'test_channel_456'}
            response = self.client.post('/api/layouts/test_group_123/reload', json=payload)
            self.assertEqual(response.status_code, 500)
            data = response.get_json()
            self.assertIn('Layout generation failed', data['error'])

    def test_update_border_success(self):
        """Тест успешного обновления border_width"""
        with self.app.app_context():
            # Создаем тестовый layout
            layout = Layout(
                grouped_id='test_group_123',
                channel_id='test_channel_456',
                json_data={'total_width': 100, 'total_height': 200, 'cells': []}
            )
            db.session.add(layout)
            db.session.commit()

            payload = {
                'channel_id': 'test_channel_456',
                'border_width': '10'
            }
            response = self.client.patch('/api/layouts/test_group_123/border', json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('layout', data)
            self.assertEqual(data['layout']['border_width'], '10')

            # Проверяем обновление в БД
            updated_layout = Layout.query.filter_by(grouped_id='test_group_123', channel_id='test_channel_456').first()
            self.assertEqual(updated_layout.json_data['border_width'], '10')

    def test_update_border_not_found(self):
        """Тест обновления border_width для несуществующего layout"""
        payload = {
            'channel_id': 'test_channel_456',
            'border_width': '10'
        }
        response = self.client.patch('/api/layouts/nonexistent/border', json=payload)
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn('Layout not found', data['error'])

    def test_update_border_missing_channel_id(self):
        """Тест обновления border_width без channel_id"""
        response = self.client.patch('/api/layouts/test_group_123/border', json={'border_width': '10'})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('channel_id parameter is required', data['error'])


if __name__ == '__main__':
    unittest.main()