"""
Тесты для API редактирования (правок) постов
"""
import unittest
import json
import os
import sys

# Устанавливаем переменные окружения перед импортом app
os.environ.setdefault("API_ID", "12345")
os.environ.setdefault("API_HASH", "test_hash")
os.environ.setdefault("PHONE", "+10000000000")

from app import app
from models import db, Edit, Channel


class TestEditsAPI(unittest.TestCase):
    """Тесты для API правок постов"""

    def setUp(self):
        """Настройка тестового окружения"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Создаем тестовые каналы
            channel1 = Channel(
                id='test_channel_1',
                name='Test Channel 1',
                changes={}
            )
            channel2 = Channel(
                id='test_channel_2',
                name='Test Channel 2',
                changes={}
            )
            db.session.add(channel1)
            db.session.add(channel2)
            
            # Создаем тестовые правки
            edit1 = Edit(
                telegram_id=100,
                channel_id='test_channel_1',
                date='2024-01-01T10:00:00',
                changes={'message': 'Updated text 1'}
            )
            edit2 = Edit(
                telegram_id=101,
                channel_id='test_channel_1',
                date='2024-01-01T11:00:00',
                changes={'message': 'Updated text 2'}
            )
            edit3 = Edit(
                telegram_id=200,
                channel_id='test_channel_2',
                date='2024-01-01T12:00:00',
                changes={'hidden': True}
            )
            
            db.session.add(edit1)
            db.session.add(edit2)
            db.session.add(edit3)
            db.session.commit()

    def tearDown(self):
        """Очистка после тестов"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_all_edits(self):
        """Тест получения всех правок"""
        response = self.client.get('/api/edits')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIn('edits', data)
        self.assertEqual(len(data['edits']), 3)  # Всего 3 правки

    def test_get_edits_stats_empty(self):
        """Тест получения всех правок когда их нет"""
        with self.app.app_context():
            # Удаляем все правки
            Edit.query.delete()
            db.session.commit()
        
        response = self.client.get('/api/edits')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['edits']), 0)

    def test_delete_edits_for_channel(self):
        """Тест удаления правок для канала"""
        response = self.client.delete('/api/edits/test_channel_1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['deleted_count'], 2)
        self.assertIn('Successfully deleted 2 edits', data['message'])
        
        # Проверяем что правки удалены
        with self.app.app_context():
            remaining_edits = Edit.query.filter_by(channel_id='test_channel_1').count()
            self.assertEqual(remaining_edits, 0)
            
            # Правки другого канала должны остаться
            other_channel_edits = Edit.query.filter_by(channel_id='test_channel_2').count()
            self.assertEqual(other_channel_edits, 1)

    def test_delete_edits_for_nonexistent_channel(self):
        """Тест удаления правок для несуществующего канала"""
        response = self.client.delete('/api/edits/nonexistent_channel')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['deleted_count'], 0)
        self.assertIn('No edits found', data['message'])

    def test_create_edit(self):
        """Тест создания новой правки"""
        new_edit = {
            'telegram_id': 300,
            'channel_id': 'test_channel_1',
            'changes': {'message': 'New edit text'}
        }
        
        response = self.client.post(
            '/api/edits',
            data=json.dumps(new_edit),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'created')
        self.assertIn('edit_id', data)

    def test_update_existing_edit(self):
        """Тест обновления существующей правки"""
        updated_edit = {
            'telegram_id': 100,
            'channel_id': 'test_channel_1',
            'changes': {'message': 'Updated again'}
        }
        
        response = self.client.post(
            '/api/edits',
            data=json.dumps(updated_edit),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'updated')

    def test_get_edit_for_post(self):
        """Тест получения правки для конкретного поста"""
        response = self.client.get('/api/edits/100/test_channel_1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['edit'])
        self.assertEqual(data['edit']['telegram_id'], 100)
        self.assertEqual(data['edit']['channel_id'], 'test_channel_1')

    def test_get_edits_for_channel(self):
        """Тест получения всех правок для канала"""
        response = self.client.get('/api/edits/test_channel_1')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertTrue(data['success'])
        self.assertEqual(len(data['edits']), 2)


if __name__ == '__main__':
    unittest.main()
