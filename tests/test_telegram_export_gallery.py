from __future__ import annotations

import os
import sys
from contextlib import nullcontext
from types import ModuleType, SimpleNamespace
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class GalleryLayoutTests(TelegramExportUnitTestCase):
    def test_generate_gallery_layouts_creates_layout(self):
        image_dir = os.path.join(self.temp_dir, "channel123", "thumbs")
        os.makedirs(image_dir, exist_ok=True)
        rel1 = os.path.join("channel123", "thumbs", "img1.jpg")
        rel2 = os.path.join("channel123", "thumbs", "img2.jpg")
        open(os.path.join(self.temp_dir, rel1), "wb").close()
        open(os.path.join(self.temp_dir, rel2), "wb").close()

        fake_posts = [
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel1, telegram_id=2),
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel2, telegram_id=1),
        ]

        created_layouts = []
        session_mock = mock.Mock()

        class FakePostModel:
            query = mock.Mock()

        FakePostModel.query.filter_by.return_value.all.return_value = fake_posts

        class FakeLayout:
            query = mock.Mock()

            def __init__(self, grouped_id, channel_id, json_data):
                created_layouts.append(
                    {
                        "grouped_id": grouped_id,
                        "channel_id": channel_id,
                        "json_data": json_data,
                    }
                )

        FakeLayout.query.filter_by.return_value.first.return_value = None

        fake_models = ModuleType("models")
        fake_models.Post = FakePostModel
        fake_models.Layout = FakeLayout
        fake_models.db = SimpleNamespace(session=session_mock)

        class FakeApp:
            def app_context(self):
                return nullcontext()

        fake_app_module = ModuleType("app")
        fake_app_module.app = FakeApp()

        layout_data = {"cells": [{"image_index": 0}, {"image_index": 1}]}

        with mock.patch.dict(sys.modules, {"app": fake_app_module, "models": fake_models}):
            with mock.patch("utils.gallery_layout.generate_gallery_layout", return_value=layout_data):
                telegram_export.generate_gallery_layouts_for_channel("channel123")

        self.assertEqual(len(created_layouts), 1)
        self.assertEqual(created_layouts[0]["json_data"], layout_data)
        session_mock.add.assert_called_once()
        session_mock.commit.assert_called_once()

    def test_generate_gallery_layouts_skips_existing_layout(self):
        image_dir = os.path.join(self.temp_dir, "channel123", "thumbs")
        os.makedirs(image_dir, exist_ok=True)
        rel1 = os.path.join("channel123", "thumbs", "img1.jpg")
        rel2 = os.path.join("channel123", "thumbs", "img2.jpg")
        open(os.path.join(self.temp_dir, rel1), "wb").close()
        open(os.path.join(self.temp_dir, rel2), "wb").close()

        fake_posts = [
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel1, telegram_id=1),
            SimpleNamespace(grouped_id=111, media_type="MessageMediaPhoto", thumb_url=rel2, telegram_id=2),
        ]

        session_mock = mock.Mock()

        class FakePostModel:
            query = mock.Mock()

        FakePostModel.query.filter_by.return_value.all.return_value = fake_posts

        existing_layout = SimpleNamespace(json_data={"cells": [{"image_index": 0}, {"image_index": 1}]})

        class FakeLayout:
            query = mock.Mock()

            def __init__(self, *args, **kwargs):
                raise AssertionError("Layout should not be created when valid layout exists")

        FakeLayout.query.filter_by.return_value.first.return_value = existing_layout

        fake_models = ModuleType("models")
        fake_models.Post = FakePostModel
        fake_models.Layout = FakeLayout
        fake_models.db = SimpleNamespace(session=session_mock)

        class FakeApp:
            def app_context(self):
                return nullcontext()

        fake_app_module = ModuleType("app")
        fake_app_module.app = FakeApp()

        with mock.patch.dict(sys.modules, {"app": fake_app_module, "models": fake_models}):
            with mock.patch("utils.gallery_layout.generate_gallery_layout") as layout_mock:
                telegram_export.generate_gallery_layouts_for_channel("channel123")

        layout_mock.assert_not_called()
        session_mock.add.assert_not_called()
        session_mock.commit.assert_not_called()