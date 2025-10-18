from __future__ import annotations

import os
from unittest import mock

from tests._telegram_export_base import TelegramExportUnitTestCase, telegram_export


class TelegramExportUtilityTests(TelegramExportUnitTestCase):
    def test_should_stop_import_true(self):
        with mock.patch("telegram_export.requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "stopped"}
            self.assertTrue(telegram_export.should_stop_import("channel123"))

    def test_update_import_progress_post_called(self):
        with mock.patch("telegram_export.requests.post") as mock_post:
            telegram_export.update_import_progress("channel123", 10, 5, total_posts=100)
            mock_post.assert_called_once()

    def test_clear_downloads_removes_existing_folder(self):
        channel_folder = os.path.join(self.temp_dir, "existing")
        os.makedirs(channel_folder, exist_ok=True)
        with open(os.path.join(channel_folder, "file.txt"), "w", encoding="utf-8") as handle:
            handle.write("data")

        telegram_export.clear_downloads("existing")

        self.assertTrue(os.path.isdir(channel_folder))
        self.assertEqual(os.listdir(channel_folder), [])

    def test_get_channel_folder_numeric_id(self):
        channel_folder = telegram_export.get_channel_folder("12345")
        self.assertTrue(channel_folder.endswith(os.path.join(self.temp_dir, "channel_12345")))
        self.assertTrue(os.path.isdir(os.path.join(channel_folder, "media")))