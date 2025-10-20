import os
import tempfile
import unittest
from unittest import mock
from PIL import Image
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from utils.gallery_layout import generate_gallery_layout


class GalleryLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

        # Создаем тестовые изображения
        self.image_paths = []
        for i in range(3):
            img_path = os.path.join(self.temp_dir, f'test_image_{i}.jpg')
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            img.save(img_path)
            self.image_paths.append(img_path)

    def tearDown(self):
        # Удаляем тестовые файлы
        for path in self.image_paths:
            if os.path.exists(path):
                os.remove(path)
        # Удаляем директорию
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_generate_layout_with_default_params(self):
        """Тест генерации layout с параметрами по умолчанию"""
        result = generate_gallery_layout(self.image_paths)
        self.assertIsNotNone(result)
        self.assertIn('total_width', result)
        self.assertIn('total_height', result)
        self.assertIn('cells', result)
        self.assertEqual(result['image_count'], 3)
        self.assertGreater(len(result['cells']), 0)

    def test_generate_layout_with_columns_1(self):
        """Тест генерации layout с 1 колонкой (без кропа)"""
        result = generate_gallery_layout(self.image_paths, columns=1)
        self.assertIsNotNone(result)
        self.assertEqual(result['image_count'], 3)
        # В режиме 1 колонки все ячейки должны иметь x=0 и ширину total_width
        for cell in result['cells']:
            self.assertEqual(cell['x'], 0)
            self.assertEqual(cell['width'], result['total_width'])

    def test_generate_layout_with_columns_2(self):
        """Тест генерации layout с 2 колонками"""
        result = generate_gallery_layout(self.image_paths, columns=2)
        self.assertIsNotNone(result)
        self.assertEqual(result['image_count'], 3)

    def test_generate_layout_with_no_crop(self):
        """Тест генерации layout с no_crop=True"""
        result = generate_gallery_layout(self.image_paths, no_crop=True)
        self.assertIsNotNone(result)
        self.assertEqual(result['image_count'], 3)

    def test_generate_layout_insufficient_images(self):
        """Тест генерации layout с недостаточным количеством изображений"""
        result = generate_gallery_layout(self.image_paths[:1])
        self.assertIsNone(result)

    def test_generate_layout_missing_image(self):
        """Тест генерации layout с отсутствующим изображением"""
        missing_path = os.path.join(self.temp_dir, 'missing.jpg')
        paths = self.image_paths + [missing_path]
        result = generate_gallery_layout(paths)
        self.assertIsNone(result)

    def test_generate_layout_columns_out_of_range(self):
        """Тест генерации layout с количеством колонок вне диапазона"""
        # columns=5 должно быть ограничено до 3 (len(photos))
        result = generate_gallery_layout(self.image_paths, columns=5)
        self.assertIsNotNone(result)

    def test_generate_layout_columns_none(self):
        """Тест генерации layout с columns=None (авто-режим)"""
        result = generate_gallery_layout(self.image_paths, columns=None)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()